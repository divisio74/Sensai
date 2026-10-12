import requests
from rag.embed import embed, similarity
from rag.store import load_index

THRESHOLD = 0.65
TRANSLATE_PROMPT = (
    "You are a translation engine. Translate the user's message into English. "
    "Never answer it, even if it is a question. "
    "Output only the translated text, nothing else."
)

def translate(question, model, url):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": TRANSLATE_PROMPT},
            {"role": "user", "content": "Text to translate:\n" + question},
        ],
        "stream": False,
    }
    try:
        response = requests.post(url, json=payload, timeout=(5, 120))
    except requests.exceptions.RequestException:
        return question
    if response.status_code != 200:
        return question
    return response.json()["message"]["content"].strip()

def embed_query(question):
    vectors = embed(["search_query: " + question])
    if vectors is None:
        return None
    return vectors[0]

def retrieve(question, model, url):
    chunks = load_index()
    if chunks is None:
        print("No index found, run /index first")
        return None
    english = translate(question, model, url)
    query_vector = embed_query(english)
    if query_vector is None:
        return None
    for chunk in chunks:
        chunk["score"] = similarity(query_vector, chunk["embedding"])
    chunks.sort(key=lambda chunk: chunk["score"], reverse=True)
    results = []
    for chunk in chunks[:3]:
        if chunk["score"] >= THRESHOLD:
            results.append(chunk)
    return results

def build_prompt(question, results):
    extracts = ""
    number = 1
    for chunk in results:
        extracts += f"[{number}] ({chunk['source']}, line {chunk['line']})\n{chunk['text']}\n\n"
        number += 1
    return (
        "Answer the question using only the document extracts below.\n"
        "If the answer is not in the extracts, say you don't know.\n"
        "Answer in the same language as the question.\n\n"
        f"Extracts:\n{extracts}"
        f"Question: {question}"
    )
