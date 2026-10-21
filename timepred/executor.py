import time

from core.boucle import code_cycle
from timepred.plan import CODE_TYPE
from timepred.worker import run_step_as_subprocess


def run_code_step(step, task, previous, model, url):
    request = f"{task}\nCurrent step: {step['name']}"
    if previous:
        request += f"\nPrevious result (truncated): {previous[-800:]}"
    start = time.perf_counter()
    result = code_cycle(request, model, url)
    duration = time.perf_counter() - start
    ok = result["status"] == "success"
    output = f"```python\n{result['code'] or ''}\n```"
    if ok:
        output += f"\nOutput:\n{result['stdout']}"
    return duration, ok, output, None


def run_step(step, task, previous, model, url, on_progress=None, max_words=None):
    if step["type"] == CODE_TYPE:
        return run_code_step(step, task, previous, model, url)
    return run_step_as_subprocess(step, task, previous, model, url, on_progress, max_words)
