import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
STEP_TIMEOUT = 300


def ask_ollama(model, messages, url=OLLAMA_URL, schema=None):
    payload = {"model": model, "messages": messages, "stream": False}
    if schema:
        payload["format"] = schema
    response = requests.post(url, json=payload, timeout=STEP_TIMEOUT)
    response.raise_for_status()
    return response.json()["message"]["content"]
