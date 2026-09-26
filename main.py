
import requests
import json

URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:3b"


def chat(messages):
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": True,
    }
    response = requests.post(URL, json=payload, stream=True)

    full_reply = ""
    for line in response.iter_lines():
        chunk = json.loads(line)
        morceau = chunk["message"]["content"]
        print(morceau, end="", flush=True)
        full_reply += morceau
    print()
    return full_reply


messages = []

while True:
    try:
        user_input = input("Vous: ")
    except (EOFError, KeyboardInterrupt):
        print("\nSALAM le sang")
        break

    if not user_input.strip():
        continue

    if user_input == "quit":
        break

    messages.append({"role": "user", "content": user_input})       # ⑥ un dict {role, content} — quel rôle ?
    print("Sensia: ", end="", flush=True)
    reply = chat(messages)
    messages.append({"role": "assistant", "content": reply})       # ⑦ un dict {role, content} — quel rôle cette fois ?
