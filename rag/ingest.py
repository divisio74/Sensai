import os

EXTENSIONS = (".md", ".txt", ".py")
CHUNK_SIZE = 500
OVERLAP = 100

def chunk_text(text, source):
    chunks = []
    start = 0

    while start < len(text):
        piece = text[start:start + CHUNK_SIZE]
        if piece.strip():
            chunks.append({
                "text": piece,
                "source": source,
                "line": text.count("\n", 0, start) + 1,
            })
        start += CHUNK_SIZE - OVERLAP
    return chunks

def ingest():
    folder="knowledge/documents"
    chunks = []

    for root, _, files in os.walk(folder):
        for name in files:
            if not name.endswith(EXTENSIONS):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
            except (OSError, UnicodeDecodeError):
                print(f"Cannot read {path}, skipped")
                continue
            chunks += chunk_text(text, path)
    return chunks
