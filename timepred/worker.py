import json
import subprocess
import sys
import time
from pathlib import Path

from timepred.llm import STEP_TIMEOUT, ask_ollama

ROOT = Path(__file__).resolve().parent.parent


def run_worker(step_json):
    step = json.loads(step_json)
    answer = ask_ollama(step["model"], [
        {"role": "system", "content": "You execute the given step of a task. Be concise."},
        {"role": "user", "content":
            f"Overall task: {step['task']}\n"
            f"Previous result (truncated): {step['previous'][-800:]}\n"
            f"Your step: {step['name']}"},
    ], url=step["url"])
    print(answer)


def run_step_as_subprocess(step, task, previous, model, url):
    payload = json.dumps({"name": step["name"], "task": task,
                          "previous": previous, "model": model, "url": url})
    start = time.perf_counter()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "timepred.worker", payload],
            capture_output=True, text=True, timeout=STEP_TIMEOUT, cwd=ROOT,
        )
        ok, output = result.returncode == 0, result.stdout
    except subprocess.TimeoutExpired:
        ok, output = False, ""
    return time.perf_counter() - start, ok, output


if __name__ == "__main__":
    run_worker(sys.argv[1])
