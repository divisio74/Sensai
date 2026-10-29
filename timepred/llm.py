import requests

from core.config import CONFIG, options

OLLAMA_URL = CONFIG["ollama"]["chat_url"]
STEP_TIMEOUT = CONFIG["timepred"]["step_timeout"]


def ask_ollama(model, messages, url=OLLAMA_URL, schema=None, usage="plan"):
    payload = {"model": model, "messages": messages, "stream": False, "options": options(usage)}
    if schema:
        payload["format"] = schema
    response = requests.post(url, json=payload, timeout=STEP_TIMEOUT)
    response.raise_for_status()
    return response.json()["message"]["content"]
