import argparse
import requests

from core.llm import chat
from core.boucle import code_cycle
from core.persona import load_persona, build_system_prompt


def u_send_message_a(content, messages, model, url):
    messages.append({"role": "user", "content": content})
    print("Sensia: ", end="", flush=True)
    reply = chat(messages, model, url)
    if reply is None:
        messages.pop()
        return
    messages.append({"role": "assistant", "content": reply})


def parse_args():
    parser = argparse.ArgumentParser(description="Sensia: Local assistant")
    parser.add_argument("--model", default="qwen2.5:3b", help="...")
    parser.add_argument("--url", default="http://localhost:11434/api/chat", help="...")
    return parser.parse_args()


def check_ollama(model, url):
    try:
        response = requests.post(url, json={"model": model, "messages": []}, timeout=(5, 120))
    except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError):
        print("\nServer unreachable")
        return None
    except requests.exceptions.Timeout:
        print("\nOllama stopped responding (timeout)")
        return None
    except requests.exceptions.RequestException as e:
        print(f"\nInvalid request: {e}")
        return None
    if response.status_code != 200:
        print("Bad url OR model ! : ", response.status_code)
        return None
    return True


def main():
    args = parse_args()
    model = args.model
    url = args.url

    if not check_ollama(model, url):
        return
    persona_text = load_persona("sensia")
    system_message = build_system_prompt(persona_text)
    messages = [system_message]

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

        if user_input.startswith("/code "):
            task = user_input[len("/code "):]
            if not task.strip():
                print("Usage: /code <task>")
                continue
            cc_output = code_cycle(task, model, url)
            if cc_output["status"] == "success":
                content = "Here is the code you need :" + cc_output["code"] + "and the result of his execution :" + cc_output["stdout"]
                u_send_message_a(content, messages, model, url)
                continue
            else:
                content = "Unfortunetely its impossible to do this actually ask me to remake my goals !"
                u_send_message_a(content, messages, model, url)
                continue

        u_send_message_a(user_input, messages, model, url)


if __name__ == "__main__":
    main()
