"""Benchmark of local models on this machine: speed, memory and code-loop success.

    python3 -m benchmarks.models                       # qwen2.5:1.5b, qwen2.5:3b, qwen2.5:7b
    python3 -m benchmarks.models qwen2.5:3b llama3.2:3b

Each model is unloaded before it is measured, so the load time is a cold start.
Results are printed as a Markdown table and saved in benchmarks/results/models.json.
"""
import contextlib
import io
import json
import platform
import statistics
import subprocess
import sys
import time

import requests

from core.boucle import code_cycle
from core.config import CONFIG, ROOT, options

BASE = CONFIG["ollama"]["chat_url"].rsplit("/api/", 1)[0]
DEFAULT_MODELS = ["qwen2.5:1.5b", "qwen2.5:3b", "qwen2.5:7b"]
SEED = 42
PROMPTS = [
    ("chat", "Écris un mail de relance poli pour une réunion lundi à 10h."),
    ("chat", "Explain the difference between a list and a tuple in Python, for a beginner."),
    ("code", "Write a Python function that checks whether a string is a palindrome, with 3 examples."),
    ("rag", "Answer in one sentence: what is a vector embedding?"),
]
CODE_TASKS = [
    "Write a Python function that returns the first 15 Fibonacci numbers and print them",
    "Write a Python function that checks if a string is a palindrome and test it on 5 words",
    "Write a Python function that converts Roman numerals to integers and print 3 examples",
    "Parse the CSV string 'name,age\\nAna,17\\nBob,22\\nCyd,30', keep rows where age >= 18 and print the count",
    "Write a Python function that returns the prime numbers below 50 and print them",
]


def unload_all():
    for loaded in requests.get(f"{BASE}/api/ps", timeout=10).json().get("models", []):
        requests.post(f"{BASE}/api/generate", json={"model": loaded["name"], "keep_alive": 0}, timeout=60)


def model_details(model):
    show = requests.post(f"{BASE}/api/show", json={"model": model}, timeout=30).json()["details"]
    disk = next(m["size"] for m in requests.get(f"{BASE}/api/tags", timeout=10).json()["models"]
                if m["name"] == model)
    return {"family": show.get("family"), "parameters": show.get("parameter_size"),
            "quantization": show.get("quantization_level"), "disk_gb": round(disk / 1e9, 2)}


def generate(model, usage, prompt):
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False,
               "options": {**options(usage), "seed": SEED}}
    r = requests.post(CONFIG["ollama"]["chat_url"], json=payload, timeout=600).json()
    return {"load_s": r["load_duration"] / 1e9,
            "prompt_tps": r["prompt_eval_count"] / max(r["prompt_eval_duration"] / 1e9, 1e-9),
            "gen_tps": r["eval_count"] / max(r["eval_duration"] / 1e9, 1e-9),
            "tokens": r["eval_count"], "total_s": r["total_duration"] / 1e9}


def memory_gb(model):
    for loaded in requests.get(f"{BASE}/api/ps", timeout=10).json().get("models", []):
        if loaded["name"] == model:
            return round(loaded["size"] / 1e9, 2)
    return None


def code_success(model):
    attempts, successes, durations = [], 0, []
    for task in CODE_TASKS:
        start = time.perf_counter()
        with contextlib.redirect_stdout(io.StringIO()):
            result = code_cycle(task, model, CONFIG["ollama"]["chat_url"])
        durations.append(time.perf_counter() - start)
        if result["status"] == "success":
            successes += 1
            attempts.append(result["tentatives"])
    return {"code_success": f"{successes}/{len(CODE_TASKS)}",
            "code_attempts": round(statistics.mean(attempts), 2) if attempts else None,
            "code_median_s": round(statistics.median(durations), 1)}


def machine():
    cpu = next((line.split(":", 1)[1].strip() for line in
                subprocess.run(["lscpu"], capture_output=True, text=True).stdout.splitlines()
                if line.startswith("Model name")), platform.processor())
    with open("/proc/meminfo") as f:
        ram = int(f.readline().split()[1]) / 1e6
    return {"cpu": cpu, "ram_gb": round(ram, 1), "ollama": requests.get(f"{BASE}/api/version", timeout=10).json()["version"]}


def bench(model):
    unload_all()
    runs = [generate(model, usage, prompt) for usage, prompt in PROMPTS]
    return {"model": model, **model_details(model), "memory_gb": memory_gb(model),
            "cold_load_s": round(runs[0]["load_s"], 1),
            "prompt_tps": round(statistics.median(r["prompt_tps"] for r in runs), 1),
            "gen_tps": round(statistics.median(r["gen_tps"] for r in runs), 1),
            "median_answer_s": round(statistics.median(r["total_s"] for r in runs[1:]), 1),
            **code_success(model)}


def main():
    models = sys.argv[1:] or DEFAULT_MODELS
    info = machine()
    print(f"Machine: {info['cpu']}, {info['ram_gb']} GB RAM, Ollama {info['ollama']}, num_ctx "
          f"{CONFIG['generation']['num_ctx']}, CPU only\n")
    results = []
    for model in models:
        print(f"... {model}", flush=True)
        results.append(bench(model))
    unload_all()
    columns = ["model", "parameters", "quantization", "disk_gb", "memory_gb", "cold_load_s",
               "prompt_tps", "gen_tps", "median_answer_s", "code_success", "code_attempts", "code_median_s"]
    print("\n| " + " | ".join(columns) + " |\n|" + "---|" * len(columns))
    for r in results:
        print("| " + " | ".join(str(r[c]) for c in columns) + " |")
    out = ROOT / "benchmarks" / "results" / "models.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    previous = json.loads(out.read_text(encoding="utf-8"))["results"] if out.exists() else []
    measured = {r["model"] for r in results}
    results = [r for r in previous if r["model"] not in measured] + results
    out.write_text(json.dumps({"machine": info, "results": results}, indent=2), encoding="utf-8")
    print(f"\nSaved to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
