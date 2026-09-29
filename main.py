import argparse

from core.llm import chat

parser = argparse.ArgumentParser(description="Sensia: Local assistant")
parser.add_argument("--model", default="qwen2.5:3b", help="...")
parser.add_argument("--url", default="http://localhost:11434/api/chat", help="...")
args = parser.parse_args()

MODEL = args.model
URL = args.url

messages = []

while True:
    try:
        user_input = input("You: ")
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye")
        break

    if not user_input.strip():
        continue

    if user_input == "quit":
        break

    messages.append({"role": "user", "content": user_input})
    print("Sensia: ", end="", flush=True)
    reply = chat(messages, MODEL, URL)
    if reply is None:
        messages.pop()
        continue

    messages.append({"role": "assistant", "content": reply})
