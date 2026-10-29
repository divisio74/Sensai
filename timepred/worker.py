import json
import subprocess
import sys
import time
from pathlib import Path

import requests

from core.config import options
from timepred.llm import STEP_TIMEOUT

ROOT = Path(__file__).resolve().parent.parent
SYSTEM_PROMPT = ("You execute the given step of a task. Be concise. "
                 "Always answer in the language of the overall task.")


def emit(event):
    print(json.dumps(event), flush=True)


def run_worker(step_json):
    step = json.loads(step_json)
    system = SYSTEM_PROMPT
    if step.get("max_words"):
        system += f" Answer in about {step['max_words']} words."
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content":
            f"Overall task: {step['task']}\n"
            f"Previous result (truncated): {step['previous'][-800:]}\n"
            f"Your step: {step['name']}"},
    ]
    with requests.post(step["url"], json={"model": step["model"], "messages": messages,
                                          "stream": True, "options": options("task")},
                       stream=True, timeout=STEP_TIMEOUT) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            text = chunk.get("message", {}).get("content", "")
            if text:
                emit({"text": text})
            if chunk.get("done"):
                emit({"done": True, "tokens": chunk.get("eval_count", 0),
                      "gen_time": chunk.get("eval_duration", 0) / 1e9})


def run_step_as_subprocess(step, task, previous, model, url, on_progress=None, max_words=None):
    payload = json.dumps({"name": step["name"], "task": task, "previous": previous,
                          "model": model, "url": url, "max_words": max_words})
    start = time.perf_counter()
    process = subprocess.Popen([sys.executable, "-m", "timepred.worker", payload],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True, cwd=ROOT)
    parts, info = [], {"tokens": 0, "gen_time": 0.0, "stopped": False}
    for line in process.stdout:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if "text" in event:
            parts.append(event["text"])
            info["tokens"] += 1
            if on_progress and not on_progress(info["tokens"], time.perf_counter() - start):
                info["stopped"] = True
                process.kill()
                break
        elif event.get("done"):
            info["tokens"], info["gen_time"] = event["tokens"] or info["tokens"], event["gen_time"]
    process.wait()
    ok = info["stopped"] or process.returncode == 0
    return time.perf_counter() - start, ok, "".join(parts), info


if __name__ == "__main__":
    run_worker(sys.argv[1])
