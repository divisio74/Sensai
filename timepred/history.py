import json
import math
from pathlib import Path

from rag.embed import embed, similarity

ROOT = Path(__file__).resolve().parent.parent
HISTORY_PATH = ROOT / "knowledge" / "history" / "time_history.json"
TASKS_PATH = ROOT / "knowledge" / "history" / "task_history.json"
DEFAULT_MEAN = 20.0
MIN_REL_STD = 0.25
K_NEIGHBORS = 5
MIN_SIMILARITY = 0.7


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


def history_prior(steps, history, model, near):
    total, variance = 0.0, 0.0
    for step in steps:
        durations = near.get(step["type"]) or history.get(model, {}).get(step["type"], [])
        mean, std = step_stats(durations)
        total += mean
        variance += std ** 2
    return total, math.sqrt(variance)
