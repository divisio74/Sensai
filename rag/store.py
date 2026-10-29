import json
import os

from core.config import CONFIG, path

INDEX_PATH = path(CONFIG["rag"]["index_path"])

def save_index(chunks):
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f)

def load_index():
    if not os.path.exists(INDEX_PATH):
        return None
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)
