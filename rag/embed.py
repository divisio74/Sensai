import requests

EMBED_MODEL = "nomic-embed-text"
EMBED_URL = "http://localhost:11434/api/embed"
BATCH_SIZE = 32

def embed(texts):
    try:
        response = requests.post(EMBED_URL, json={"model": EMBED_MODEL, "input": texts}, timeout=(5, 120))
    except requests.exceptions.RequestException as e:
        print(f"Embeddind error: {e}")
        return None
    if response.status_code != 200:
        print("Embedding error")
        return None
    return response.json()["embeddings"]

def embed_chunks(chunks):
    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start:start + BATCH_SIZE]
        texts = []
        for chunk in batch:
            texts.append("search_document: " + chunk["text"])
        vectors = embed(texts)
        if vectors is None:
            return False
        for j in range(len(batch)):
            batch[j]["embedding"] = vectors[j]
        done = min(start + BATCH_SIZE, len(chunks))
        print(f"{done}/{len(chunks)} chunks embedded")
    return True

def similarity(vector_a, vector_b):
    total = 0
    for i in range(len(vector_a)):
        total += vector_a[i] * vector_b[i]
    return total
