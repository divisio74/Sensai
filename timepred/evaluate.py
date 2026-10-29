import statistics as st

from timepred.history import TASKS_PATH, load_json

PHASES = [("p < 60 %", 0.0, 0.6), ("60-80 %", 0.6, 0.8), ("80-99 %", 0.8, 1.0)]
METHODS = [("frozen", "p_frozen"), ("re-estimated", "p_live"), ("calibrated", "p_calib")]


def error(point, key, total):
    p = point.get(key, point["p_live"])
    return abs(point["elapsed"] / p - total) / total


def evaluate():
    traced = [task for task in load_json(TASKS_PATH, []) if task.get("trace")]
    for task in traced:
        task["trace"] = [point for point in task["trace"] if not point.get("live")]
    reestimated = sum(point["reestimated"] for task in traced for point in task["trace"])
    print(f"{len(traced)} tasks with a trace, {reestimated} re-estimations")
    for label, low, high in PHASES:
        points = [(point, task["total"]) for task in traced for point in task["trace"]
                  if point["p_frozen"] < 1 and low <= point["p_frozen"] < high]
        if not points:
            print(f"{label:<9}   no point")
            continue
        scores = " | ".join(f"{name} {st.median(error(pt, key, total) for pt, total in points):4.0%}"
                            for name, key in METHODS)
        print(f"{label:<9} {len(points):>3} points | {scores}")


if __name__ == "__main__":
    evaluate()
