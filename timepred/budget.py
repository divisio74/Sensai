from timepred.history import history_prior
from timepred.plan import PRUNABLE_TYPES


def prune_for_budget(steps, budget, history, model, near, profile=None):
    kept, removed = list(steps), []
    prunable = sorted((s for s in steps if s["type"] in PRUNABLE_TYPES and not s["essential"]),
                      key=lambda s: -s["priority"])
    for step in prunable:
        if history_prior(kept, history, model, near, profile)[0] <= budget or len(kept) == 1:
            break
        kept.remove(step)
        removed.append(step["name"])
    return kept, removed


def replan_for_budget(steps, weights, done_count, corrections, predicted_work, elapsed,
                      overhead, budget):
    remaining = range(done_count, len(steps))
    corrected = {k: weights[k] * corrections.get(steps[k]["type"], 1.0) for k in remaining}
    remaining_time = max(predicted_work - elapsed, 0.0)
    total = sum(corrected.values()) or 1.0
    predicted = elapsed + overhead + remaining_time
    prunable = sorted((k for k in remaining
                       if steps[k]["type"] in PRUNABLE_TYPES and not steps[k]["essential"]),
                      key=lambda k: -steps[k]["priority"])
    dropped = set()
    for k in prunable:
        if predicted <= budget:
            break
        dropped.add(k)
        predicted -= remaining_time * corrected[k] / total
    keep = [k for k in range(len(steps)) if k not in dropped]
    return ([steps[k] for k in keep], [weights[k] for k in keep],
            [steps[k]["name"] for k in sorted(dropped)], predicted)


def ask_to_continue(message):
    print(message)
    try:
        answer = input("   Continue anyway? [y/N] ").strip().lower()
    except EOFError:
        answer = ""
    return answer == "y"


def confirm_over_budget(t_hist, s_hist, budget):
    return ask_to_continue(f"\nBudget: {budget:.0f}s -> minimum estimate (steps that cannot be "
                           f"dropped): {t_hist:.0f}s ± {s_hist:.0f}s")


def confirm_mid_run(predicted, budget):
    return ask_to_continue(f"\nBudget: {budget:.0f}s -> updated prediction: {predicted:.0f}s, "
                           f"even after dropping the optional steps")
