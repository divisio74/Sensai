import math
import time

from timepred.budget import confirm_mid_run, confirm_over_budget, prune_for_budget, replan_for_budget
from timepred.executor import run_step
from timepred.fusion import P_MIN_PROG, bayesian_fusion, progression_prior
from timepred.history import (HISTORY_PATH, MIN_REL_STD, TASKS_PATH, embed_task, find_neighbors,
                              history_prior, load_json, neighbor_durations, save_json,
                              token_stats, weight_corrections)
from timepred.plan import CODE_TYPE, PRODUCTION_TYPES, make_plan

MAX_RESULT_CHARS = 1500
P_STEP_MAX = 0.99
PRINT_EVERY = 0.5
TOKEN_MARGIN = 0.8
WORDS_PER_TOKEN = 0.75
MIN_WORDS = 40


def progress(weights, steps, done_count, corrections):
    corrected = [w * corrections.get(step["type"], 1.0) for w, step in zip(weights, steps)]
    return sum(corrected[:done_count]) / sum(corrected)


def run(task, model, url, budget=None, allow_direct=True):
    start = time.perf_counter()
    history = load_json(HISTORY_PATH, {})
    tasks = load_json(TASKS_PATH, [])
    vector = embed_task(task)
    neighbors = find_neighbors(vector, tasks, model)
    near = neighbor_durations(neighbors)
    steps = make_plan(task, model, url, allow_direct)
    setup = time.perf_counter() - start

    print("PLAN")
    for step in steps:
        flag = "essential" if step["essential"] else "optional "
        print(f"  - [{step['type']:<13}] w={step['weight']} prio={step['priority']} "
              f"{flag}  {step['name']}")

    print(f"\nSimilar past tasks: {len(neighbors)}/{len(tasks)}")
    for score, past in neighbors:
        print(f"  {score:.2f}  {past['prompt'][:70]}")

    profile = token_stats(tasks, model, neighbors)
    removed = []
    if budget is not None:
        steps, removed = prune_for_budget(steps, budget - setup, history, model, near, profile)
        for name in removed:
            print(f"  ✂ dropped for budget: {name}")
        t_hist, s_hist = history_prior(steps, history, model, near, profile)
        if setup + t_hist - s_hist > budget and not confirm_over_budget(setup + t_hist, s_hist, budget):
            print("Cancelled.")
            return {"status": "cancelled"}

    t_hist, s_hist = history_prior(steps, history, model, near, profile)
    t_type, s_type = history_prior(steps, history, model, {})
    corrections = weight_corrections(tasks, model)
    if corrections:
        print("Learned weight corrections: "
              + ", ".join(f"{name} x{factor:.2f}" for name, factor in sorted(corrections.items())))
    if profile["speed"]:
        print(f"Learned speed: {profile['speed']:.1f} tokens/s, latency {profile['latency']:.1f}s | "
              "expected answer length: " + ", ".join(
                  f"{k} {v:.0f} tokens" for k, v in sorted(profile["expected"].items())))
    print(f"\nInitial prediction (history only): {setup + t_hist:.0f}s ± {s_hist:.0f}s"
          f" = {setup:.0f}s of setup (embedding + plan, already spent) + {t_hist:.0f}s of work"
          f"   [step type only: {t_type:.0f}s ± {s_type:.0f}s of work]\n")

    done_weight, elapsed, overhead, previous = 0, 0.0, 0.0, ""
    run_steps, code_oks, trace, live_weights, deliverables = [], [], [], None, []
    i, asked, stopped = 0, False, False
    while i < len(steps):
        step = steps[i]
        i += 1
        weights = live_weights or [s["weight"] for s in steps]
        corrected = [w * corrections.get(s["type"], 1.0) for w, s in zip(weights, steps)]
        done_part, step_part = sum(corrected[:i - 1]) / sum(corrected), corrected[i - 1] / sum(corrected)
        t_step, s_step = history_prior([step], history, model, near, profile)
        t_rest, s_rest = history_prior(steps[i:], history, model, near, profile)
        expected = profile["expected"].get(step["type"])
        max_words = None
        if budget is not None and profile["speed"] and expected and step["type"] != CODE_TYPE:
            available = budget - setup - overhead - elapsed - t_rest - profile["latency"]
            fit = profile["speed"] * available * TOKEN_MARGIN
            if fit < expected:
                max_words = max(int(fit * WORDS_PER_TOKEN), MIN_WORDS)
                expected = max_words / WORDS_PER_TOKEN
                target = profile["latency"] + expected / profile["speed"]
                print(f"  ✂ answer shortened to ~{max_words} words to fit the budget "
                      f"(~{target:.0f}s instead of ~{t_step:.0f}s)")
                t_step, s_step = target, MIN_REL_STD * target
        live = {"last_print": 0.0}

        def watch(tokens, step_elapsed):
            nonlocal asked
            if expected:
                p_step = min(tokens / expected, P_STEP_MAX)
            else:
                p_step = min(step_elapsed / max(t_step, 1e-9), P_STEP_MAX)
            p_live = done_part + step_part * p_step
            now = elapsed + step_elapsed
            t_h = now + t_step * (1 - p_step) + t_rest
            s_h = max(math.hypot(s_step * (1 - p_step), s_rest), 1e-9)
            tp, sp = progression_prior(now, p_live)
            t_live, sigma_live, _ = bayesian_fusion(t_h, s_h, tp, sp)
            if step_elapsed - live["last_print"] >= PRINT_EVERY:
                live["last_print"] = step_elapsed
                print(f"\r  ⏳ {tokens:4d} tokens | p={p_live:4.0%} | "
                      f"-> {setup + overhead + t_live:.0f}±{sigma_live:.0f}s total   ",
                      end="", flush=True)
                live["printed"] = True
                trace.append({"elapsed": round(now, 2), "p_calib": round(p_live, 4),
                              "tokens": tokens, "live": True})
            over = setup + overhead + now > budget if budget is not None else False
            if budget is not None and (p_live >= P_MIN_PROG or over) and not asked:
                predicted_live = setup + overhead + max(t_live, tp, now)
                if predicted_live > budget:
                    asked = True
                    print()
                    if not confirm_mid_run(predicted_live, budget):
                        return False
            return True

        on_progress = watch if step["type"] != CODE_TYPE else None
        duration, ok, output, info = run_step(step, task, previous, model, url,
                                              on_progress, max_words)
        if live.get("printed"):
            print()
        if step["type"] == CODE_TYPE:
            code_oks.append(ok)
        elapsed += duration
        done_weight += step["weight"]
        p_frozen = done_weight / sum(s["weight"] for s in steps)

        if info and info["stopped"]:
            deliverables.append(output.strip() + "\n[… stopped here to respect the time budget]")
            print("Stopped during the step, keeping the partial answer.")
            stopped = True
            break
        if ok:
            done = {"type": step["type"], "duration": round(duration, 2), "weight": step["weight"]}
            if info:
                done.update(tokens=info["tokens"], gen_time=round(info["gen_time"], 2))
            if max_words:
                done["shortened"] = True
            run_steps.append(done)
            previous = output
            if step["type"] in PRODUCTION_TYPES:
                deliverables.append(output.strip())

        weights = live_weights or [s["weight"] for s in steps]
        p = progress(weights, steps, i, corrections)
        reestimated = False
        trace.append({"elapsed": round(elapsed, 2), "p_frozen": round(p_frozen, 4),
                      "p_live": round(sum(weights[:i]) / sum(weights), 4),
                      "p_calib": round(p, 4), "reestimated": reestimated})

        t_rest, s_rest = history_prior(steps[i:], history, model, near, profile)
        t_h, s_h = elapsed + t_rest, max(s_rest, 1e-9)
        t_prog, s_prog = progression_prior(elapsed, p)
        t, sigma, w = bayesian_fusion(t_h, s_h, t_prog, s_prog)
        leader = "history" if w < 0.5 else "progression"
        frozen = f" (frozen {p_frozen:.0%})" if abs(p - p_frozen) > 0.005 else ""
        print(f"[step {i}/{len(steps)} {step['type']:<13}] {'ok ' if ok else 'ERR'} "
              f"{duration:5.1f}s | p={p:4.0%}{frozen}{' re-estimated' if reestimated else ''} "
              f"elapsed={elapsed:5.1f}s | hist={t_h:.0f}±{s_h:.0f} "
              f"prog={'ignored' if math.isinf(s_prog) else f'{t_prog:.0f}±{s_prog:.0f}'} | "
              f"w={w:.2f} ({leader}) -> {setup + overhead + t:.0f}±{sigma:.0f}s total, "
              f"~{max(t - elapsed, 0):.0f}s left")

        if budget is not None and i < len(steps) and p >= P_MIN_PROG:
            steps, kept_weights, dropped, predicted = replan_for_budget(
                steps, weights, i, corrections, max(t, t_prog), elapsed, setup + overhead, budget)
            if live_weights:
                live_weights = kept_weights
            for name in dropped:
                print(f"  ✂ dropped mid-run for budget: {name}")
            removed += dropped
            trace[-1]["dropped"] = dropped
            if predicted > budget and not asked:
                asked = True
                if not confirm_mid_run(predicted, budget):
                    print("Stopped before the end, keeping the steps already done.")
                    stopped = True
                    break

    for done in (step for step in run_steps if not step.get("shortened")):
        history.setdefault(model, {}).setdefault(done["type"], []).append(done["duration"])
    save_json(HISTORY_PATH, history)
    if vector is not None:
        tasks.append({"model": model, "prompt": task, "embedding": vector,
                      "steps": run_steps, "total": round(elapsed, 2), "setup": round(setup, 2),
                      "overhead": round(overhead, 2), "trace": trace})
        save_json(TASKS_PATH, tasks)

    error, error_type = abs(t_hist - elapsed), abs(t_type - elapsed)
    if stopped or any(done.get("shortened") for done in run_steps):
        comparison = " | answer cut or shortened for the budget: no prediction error to compute"
    else:
        comparison = (f" | work prediction: {t_hist:.0f}s (error {error / elapsed:.0%}) | "
                      f"step type only: {t_type:.0f}s (error {error_type / elapsed:.0%})")
    print(f"\nReal: {setup + elapsed + overhead:.0f}s in total = {setup:.0f}s of setup + "
          f"{elapsed:.0f}s of work"
          + (f" + {overhead:.0f}s of re-estimation" if overhead else "") + comparison)
    if budget is not None:
        print(f"Budget: {budget:.0f}s -> {'kept' if setup + elapsed + overhead <= budget else 'exceeded'}")

    result = ("\n\n".join(deliverables) or previous.strip())[:MAX_RESULT_CHARS]
    print(f"\nRESULT\n{result}")
    return {"status": "stopped" if stopped else "done", "budget": budget,
            "elapsed": setup + elapsed + overhead, "setup": setup, "overhead": overhead,
            "predicted": setup + t_hist, "removed": removed, "result": result,
            "code_verified": all(code_oks) if code_oks else None}
