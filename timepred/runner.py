import math

from timepred.budget import confirm_over_budget, prune_for_budget
from timepred.executor import run_step
from timepred.fusion import bayesian_fusion, progression_prior
from timepred.history import (HISTORY_PATH, TASKS_PATH, embed_task, find_neighbors,
                              history_prior, load_json, neighbor_durations, save_json)
from timepred.plan import CODE_TYPE, make_plan

MAX_RESULT_CHARS = 1500


def run(task, model, url, budget=None, allow_direct=True):
    history = load_json(HISTORY_PATH, {})
    tasks = load_json(TASKS_PATH, [])
    vector = embed_task(task)
    neighbors = find_neighbors(vector, tasks, model)
    near = neighbor_durations(neighbors)
    steps = make_plan(task, model, url, allow_direct)

    print("PLAN")
    for step in steps:
        flag = "essential" if step["essential"] else "optional "
        print(f"  - [{step['type']:<13}] w={step['weight']} prio={step['priority']} "
              f"{flag}  {step['name']}")

    print(f"\nSimilar past tasks: {len(neighbors)}/{len(tasks)}")
    for score, past in neighbors:
        print(f"  {score:.2f}  {past['prompt'][:70]}")

    removed = []
    if budget is not None:
        steps, removed = prune_for_budget(steps, budget, history, model, near)
        for name in removed:
            print(f"  ✂ dropped for budget: {name}")
        t_hist, s_hist = history_prior(steps, history, model, near)
        if t_hist - s_hist > budget and not confirm_over_budget(t_hist, s_hist, budget):
            print("Cancelled.")
            return {"status": "cancelled"}

    t_hist, s_hist = history_prior(steps, history, model, near)
    t_type, s_type = history_prior(steps, history, model, {})
    total_weight = sum(step["weight"] for step in steps)
    print(f"\nInitial prediction (history only): {t_hist:.0f}s ± {s_hist:.0f}s"
          f"   [step type only: {t_type:.0f}s ± {s_type:.0f}s]\n")

    done_weight, elapsed, previous, run_steps, code_oks = 0, 0.0, "", [], []
    for i, step in enumerate(steps, 1):
        duration, ok, output = run_step(step, task, previous, model, url)
        if step["type"] == CODE_TYPE:
            code_oks.append(ok)
        elapsed += duration
        done_weight += step["weight"]
        p = done_weight / total_weight

        if ok:
            history.setdefault(model, {}).setdefault(step["type"], []).append(round(duration, 2))
            run_steps.append({"type": step["type"], "duration": round(duration, 2)})
            previous = output

        t_prog, s_prog = progression_prior(elapsed, p)
        t, sigma, w = bayesian_fusion(t_hist, s_hist, t_prog, s_prog)
        leader = "history" if w < 0.5 else "progression"
        print(f"[step {i}/{len(steps)} {step['type']:<13}] {'ok ' if ok else 'ERR'} "
              f"{duration:5.1f}s | p={p:4.0%} elapsed={elapsed:5.1f}s | "
              f"hist={t_hist:.0f}±{s_hist:.0f} "
              f"prog={'ignored' if math.isinf(s_prog) else f'{t_prog:.0f}±{s_prog:.0f}'} | "
              f"w={w:.2f} ({leader}) -> {t:.0f}±{sigma:.0f}s, "
              f"~{max(t - elapsed, 0):.0f}s left")

    save_json(HISTORY_PATH, history)
    if vector is not None:
        tasks.append({"model": model, "prompt": task, "embedding": vector,
                      "steps": run_steps, "total": round(elapsed, 2)})
        save_json(TASKS_PATH, tasks)

    error, error_type = abs(t_hist - elapsed), abs(t_type - elapsed)
    print(f"\nReal: {elapsed:.0f}s | prediction: {t_hist:.0f}s (error {error / elapsed:.0%}) | "
          f"step type only: {t_type:.0f}s (error {error_type / elapsed:.0%})")

    result = previous.strip()[:MAX_RESULT_CHARS]
    print(f"\nRESULT\n{result}")
    return {"status": "done", "budget": budget, "elapsed": elapsed,
            "predicted": t_hist, "removed": removed, "result": result,
            "code_verified": all(code_oks) if code_oks else None}
