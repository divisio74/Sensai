import argparse

from core.llm import chat


def parse_args():
    parser = argparse.ArgumentParser(description="Sensia: Local assistant")
    parser.add_argument("--model", default="qwen2.5:3b", help="...")
    parser.add_argument("--url", default="http://localhost:11434/api/chat", help="...")
    return parser.parse_args()

def main():
    args = parse_args()
    messages = []
    model = args.model
    url = args.url

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
        reply = chat(messages, model, url)
        if reply is None:
            messages.pop()
            continue

        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
