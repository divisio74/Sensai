from timepred.history import history_prior
from timepred.plan import PRUNABLE_TYPES


def prune_for_budget(steps, budget, history, model, near):
    kept, removed = list(steps), []
    prunable = sorted((s for s in steps if s["type"] in PRUNABLE_TYPES and not s["essential"]),
                      key=lambda s: -s["priority"])
    for step in prunable:
        if history_prior(kept, history, model, near)[0] <= budget or len(kept) == 1:
            break
        kept.remove(step)
        removed.append(step["name"])
    return kept, removed


def confirm_over_budget(t_hist, s_hist, budget):
    print(f"\nBudget: {budget:.0f}s -> minimum estimate (steps that cannot be dropped): "
          f"{t_hist:.0f}s ± {s_hist:.0f}s")
    try:
        answer = input("   Continue anyway? [y/N] ").strip().lower()
    except EOFError:
        answer = ""
    return answer == "y"
