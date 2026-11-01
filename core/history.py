import json
from core.auth import DATA_DIR

def history_path(email):
    return DATA_DIR / "history" / f"{email}.json"

def load_history(email):
    file = history_path(email)
    if not file.exists():
        return []
    return json.loads(file.read_text(encoding="utf-8"))

def save_history(email, messages):
    kept = []
    for message in messages[1:]:
        if message["role"] == "user":
            kept.append(message)
        elif message["role"] == "assistant" and not message.get("tool_calls"):
            kept.append(message)
    file = history_path(email)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(kept, indent=2, ensure_ascii=False), encoding="utf-8")
