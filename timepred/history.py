import json
import math
import statistics
from pathlib import Path

from rag.embed import embed, similarity

ROOT = Path(__file__).resolve().parent.parent
HISTORY_PATH = ROOT / "knowledge" / "history" / "time_history.json"
TASKS_PATH = ROOT / "knowledge" / "history" / "task_history.json"
DEFAULT_MEAN = 20.0
MIN_REL_STD = 0.25
K_NEIGHBORS = 5
MIN_SIMILARITY = 0.7
MIN_NEIGHBOR_SAMPLES = 2
MIN_CORRECTION_SAMPLES = 2
CORRECTION_SHRINK = 3
CORRECTION_BOUNDS = (0.25, 4.0)


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def embed_task(task):
    vectors = embed(["clustering: " + task])
    return vectors[0] if vectors else None


def find_neighbors(vector, tasks, model):
    if vector is None:
        return []
    scored = [(similarity(vector, past["embedding"]), past)
              for past in tasks if past["model"] == model]
    scored = [item for item in scored if item[0] >= MIN_SIMILARITY]
    scored.sort(key=lambda item: -item[0])
    return scored[:K_NEIGHBORS]


def neighbor_durations(neighbors):
    near = {}
    for _, past in neighbors:
        for step in past["steps"]:
            if step.get("shortened"):
                continue
            near.setdefault(step["type"], []).append(step["duration"])
    return near


def step_stats(durations):
    if not durations:
        return DEFAULT_MEAN, DEFAULT_MEAN
    mean = sum(durations) / len(durations)
    if len(durations) > 1:
        std = math.sqrt(sum((d - mean) ** 2 for d in durations) / (len(durations) - 1))
    else:
        std = mean
    return mean, max(std, MIN_REL_STD * mean)


def weight_corrections(tasks, model):
    rates = {}
    for task in tasks:
        if task["model"] != model:
            continue
        for step in task["steps"]:
            if step.get("weight"):
                rates.setdefault(step["type"], []).append(step["duration"] / step["weight"])
    every = [rate for values in rates.values() for rate in values]
    if len(every) < MIN_CORRECTION_SAMPLES:
        return {}
    baseline = statistics.median(every)
    corrections = {}
    for step_type, values in rates.items():
        if len(values) < MIN_CORRECTION_SAMPLES:
            continue
        raw = statistics.median(values) / baseline
        shrunk = 1 + (raw - 1) * len(values) / (len(values) + CORRECTION_SHRINK)
        corrections[step_type] = min(max(shrunk, CORRECTION_BOUNDS[0]), CORRECTION_BOUNDS[1])
    return corrections


def token_stats(tasks, model, neighbors):
    own = [step for task in tasks if task["model"] == model for step in task["steps"]
           if not step.get("shortened")]
    close = [step for _, task in neighbors for step in task["steps"] if not step.get("shortened")]
    profile = {"expected": {}, "spread": {}, "speed": None, "latency": 0.0}
    for step_type in {step["type"] for step in own}:
        near_tokens = [s["tokens"] for s in close if s["type"] == step_type and s.get("tokens")]
        all_tokens = [s["tokens"] for s in own if s["type"] == step_type and s.get("tokens")]
        tokens = near_tokens if len(near_tokens) >= MIN_NEIGHBOR_SAMPLES else all_tokens
        if tokens:
            profile["expected"][step_type] = statistics.median(tokens)
            profile["spread"][step_type] = (statistics.stdev(all_tokens) if len(all_tokens) > 1
                                            else statistics.median(tokens))
    timed = [s for s in own if s.get("tokens") and s.get("gen_time")]
    if timed:
        profile["speed"] = statistics.median(s["tokens"] / s["gen_time"] for s in timed)
        profile["latency"] = statistics.median(s["duration"] - s["gen_time"] for s in timed)
    return profile


def history_prior(steps, history, model, near, profile=None):
    total, variance = 0.0, 0.0
    for step in steps:
        if profile and profile["speed"] and step["type"] in profile["expected"]:
            mean = profile["latency"] + profile["expected"][step["type"]] / profile["speed"]
            std = max(profile["spread"][step["type"]] / profile["speed"], MIN_REL_STD * mean)
            total += mean
            variance += std ** 2
            continue
        near_durations = near.get(step["type"], [])
        type_durations = history.get(model, {}).get(step["type"], [])
        if len(near_durations) >= MIN_NEIGHBOR_SAMPLES or not type_durations:
            durations = near_durations
        else:
            durations = type_durations
        mean, std = step_stats(durations)
        total += mean
        variance += std ** 2
    return total, math.sqrt(variance)
