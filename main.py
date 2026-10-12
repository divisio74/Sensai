import argparse
import json
import requests
# TODO avant push : décommenter (désactivé en local, python-dotenv non installé)
# from dotenv import load_dotenv

from core.llm import chat
from core.boucle import code_cycle
from core.persona import load_persona, build_system_prompt, get_persona_name, load_user_profile
from tools.internet_search import internet_search


def u_send_message_a(content, messages, model, url, name):
    messages.append({"role": "user", "content": content})
    while True:
        print(f"{name}: ", end="", flush=True)
        reply = chat(messages, model, url)
        if reply is None:
            messages.pop()
            return
        messages.append({"role": "assistant", "content": reply})

        try:
            clean_reply = reply.strip("` \n")
            if clean_reply.startswith("json"):
                clean_reply = clean_reply[4:].strip()
            parsed = json.loads(clean_reply)
            if isinstance(parsed, list) and parsed and all(isinstance(x, str) for x in parsed):
                results_text = ""
                for query in parsed:
                    print(f"\n[Internet search: {query}]")
                    try:
                        res = internet_search(query)
                        results_text += f"Results for '{query}':\n{res}\n"
                    except Exception as e:
                        results_text += f"Error searching '{query}': {e}\n"
                messages.append({"role": "user", "content": f"Here are the search results:\n{results_text}\nNow answer the user."})
                continue
        except Exception:
            pass
        break


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
    # load_dotenv()  # TODO avant push : décommenter
    args = parse_args()
    model = args.model
    url = args.url

    if not check_ollama(model, url):
        return
    persona_id = "sensia"
    persona_name = get_persona_name(persona_id)
    persona_text = load_persona(persona_id)
    user_profile = load_user_profile()
    system_message = build_system_prompt(persona_text, user_profile)
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
                u_send_message_a(content, messages, model, url, persona_name)
                continue
            else:
                content = "Unfortunetely its impossible to do this actually ask me to remake my goals !"
                u_send_message_a(content, messages, model, url, persona_name)
                continue
        if user_input.startswith("/internet_search "):
            query = user_input[len("/internet_search "):]
            if not query.strip():
                print("Usage: /internet_search <query>")
                continue
            results = internet_search(query)
            if not results or not json.loads(results):
                print("No results found.")
                continue
            u_send_message_a(query + "\n find the best answer among these results:\n" + results, messages, model, url, persona_name)
            continue

        u_send_message_a(user_input, messages, model, url, persona_name)


if __name__ == "__main__":
    main()
