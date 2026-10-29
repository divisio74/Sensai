"""Read-only backtest of the /fast prediction on the recorded history.

    python3 -m benchmarks.timepred_backtest

Each recorded run is predicted again without itself, with the same functions as the runner:
- the initial prediction, with raw durations and with "answer length / machine speed";
- the same for a new task (every copy of the task removed from the history);
- the error depending on how many times the same task had already been run (real order);
- the live prediction at 25, 50, 75 and 90 % of the generated answer.
Nothing is written.
"""
import math
import statistics as st

from timepred.fusion import bayesian_fusion, progression_prior
from timepred.history import (TASKS_PATH, find_neighbors, history_prior, load_json, neighbor_durations,
                              token_stats, weight_corrections)

MODEL = "qwen2.5:3b"
FRACTIONS = (0.25, 0.5, 0.75, 0.9)


def med(values):
    return f"{st.median(values):4.0%}" if values else "  — "


def secs(values):
    return f"{st.median(values):4.1f}s" if values else "  — "


def durations_of(tasks):
    history = {}
    for task in tasks:
        for step in task["steps"]:
            if not step.get("shortened"):
                history.setdefault(MODEL, {}).setdefault(step["type"], []).append(step["duration"])
    return history


def usable(task):
    steps = task["steps"]
    return (task["model"] == MODEL and steps
            and all(s.get("tokens") and s.get("gen_time") for s in steps if s["type"] != "code")
            and not any(s.get("shortened") for s in steps)
            and abs(sum(s["duration"] for s in steps) - task["total"]) < 0.5)


def replay(task, others):
    neighbors = find_neighbors(task.get("embedding"), others, MODEL)
    near, history = neighbor_durations(neighbors), durations_of(others)
    profile = token_stats(others, MODEL, neighbors)
    corrections = weight_corrections(others, MODEL)
    steps, total = task["steps"], task["total"]
    t_durations = history_prior(steps, history, MODEL, near)[0]
    t_tokens = history_prior(steps, history, MODEL, near, profile)[0]
    weights = [s["weight"] * corrections.get(s["type"], 1.0) for s in steps]
    live, elapsed = [], 0.0
    for k, step in enumerate(steps):
        t_step, s_step = history_prior([step], history, MODEL, near, profile)
        t_rest, s_rest = history_prior(steps[k + 1:], history, MODEL, near, profile)
        expected = profile["expected"].get(step["type"])
        if step["type"] != "code":
            latency = step["duration"] - step["gen_time"]
            for f in FRACTIONS:
                step_elapsed = latency + f * step["gen_time"]
                if expected:
                    p_step = min(f * step["tokens"] / expected, 0.99)
                else:
                    p_step = min(step_elapsed / max(t_step, 1e-9), 0.99)
                p = (sum(weights[:k]) + weights[k] * p_step) / sum(weights)
                now = elapsed + step_elapsed
                t_h = now + t_step * (1 - p_step) + t_rest
                s_h = max(math.hypot(s_step * (1 - p_step), s_rest), 1e-9)
                tp, sp = progression_prior(now, p)
                t = bayesian_fusion(t_h, s_h, tp, sp)[0]
                live.append((f, abs(t - total) / total, abs(t - total)))
        elapsed += step["duration"]
    return t_durations, t_tokens, live


def errors(task, prediction):
    return abs(prediction - task["total"]) / task["total"], abs(prediction - task["total"])


def main():
    tasks = [t for t in load_json(TASKS_PATH, []) if t["model"] == MODEL]
    good = [t for t in tasks if usable(t)]
    print(f"{len(tasks)} recorded runs, {len(good)} usable (tokens recorded, not shortened, no failure)\n")

    new = []
    for task in good:
        t_durations, t_tokens, _ = replay(task, [o for o in tasks if o["prompt"] != task["prompt"]])
        new.append(errors(task, t_durations) + errors(task, t_tokens))
    print("Initial prediction, new task (all its copies removed)")
    print(f"  raw durations        {med([x[0] for x in new])} | {secs([x[1] for x in new])}")
    print(f"  length / speed       {med([x[2] for x in new])} | {secs([x[3] for x in new])}\n")

    by_seen, live_rows = {}, {f: [] for f in FRACTIONS}
    for i, task in enumerate(tasks):
        if task not in good:
            continue
        seen = sum(1 for o in tasks[:i] if o["prompt"] == task["prompt"])
        _, t_tokens, _ = replay(task, tasks[:i])
        key = "never" if seen == 0 else "once" if seen == 1 else "twice or more"
        by_seen.setdefault(key, []).append(errors(task, t_tokens))
        for f, e, a in replay(task, [o for o in tasks if o is not task])[2]:
            live_rows[f].append((e, a))
    print("Initial prediction, depending on how often the same task was already run (real order)")
    for key in ("never", "once", "twice or more"):
        values = by_seen.get(key, [])
        print(f"  {key:<14} n={len(values):2d} | {med([x[0] for x in values])} | {secs([x[1] for x in values])}")
    print("\nLive prediction, depending on how much of the answer is written")
    for f, values in live_rows.items():
        print(f"  {f:.0%} written     n={len(values):2d} | {med([x[0] for x in values])} | {secs([x[1] for x in values])}")
    profile = token_stats(tasks, MODEL, [])
    print(f"\nLearned speed {profile['speed']:.1f} tokens/s, latency {profile['latency']:.1f}s | lengths: "
          + ", ".join(f"{k} {v:.0f}" for k, v in sorted(profile["expected"].items())))


if __name__ == "__main__":
    main()
