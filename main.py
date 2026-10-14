import argparse
import json
import requests
from dotenv import load_dotenv

from core.llm import chat
from core.boucle import code_cycle
from core.persona import load_persona, build_system_prompt
from rag.ingest import ingest
from tools.internet_search import internet_search
from rag.embed import embed_chunks
from rag.store import save_index
from rag.retrieve import retrieve, build_prompt
from timepred.runner import run as run_timed


MAX_SEARCH_ROUNDS = 3


def u_send_message_a(content, messages, model, url):
    messages.append({"role": "user", "content": content})
    search_rounds = 0
    while True:
        print("Sensia: ", end="", flush=True)
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
                search_rounds += 1
                if search_rounds > MAX_SEARCH_ROUNDS:
                    print("\n[Too many searches, stopping]")
                    break
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
    load_dotenv()
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
        if user_input.startswith("/fast"):
            parts = user_input.split(maxsplit=2)
            try:
                budget = float(parts[1])
            except (IndexError, ValueError):
                budget = 0
            if len(parts) < 3 or budget <= 0:
                print("Usage: /fast <seconds> <task>")
                continue
            task = parts[2]
            try:
                summary = run_timed(task, model, url, budget)
            except (requests.exceptions.RequestException, ValueError, KeyError) as e:
                print(f"Timed run failed: {e}")
                continue
            if summary["status"] == "cancelled":
                continue
            note = (f"[fast mode] This task actually took {summary['elapsed']:.0f} seconds "
                    f"(the user's time budget was {summary['budget']:.0f}s, "
                    f"the prediction was {summary['predicted']:.0f}s)")
            if summary["removed"]:
                note += f", dropped steps: {', '.join(summary['removed'])}"
            messages.append({"role": "user", "content": task})
            messages.append({"role": "assistant", "content": f"{note}\n\n{summary['result']}"})
            continue
        if user_input.startswith("/internet_search "):
            query = user_input[len("/internet_search "):]
            if not query.strip():
                print("Usage: /internet_search <query>")
                continue
            try:
                results = internet_search(query)
                found = json.loads(results) if results else None
            except Exception as e:
                print(f"Search failed: {e}")
                continue
            if not found:
                print("No results found.")
                continue
            u_send_message_a(query + "\n find the best answer among these results:\n" + results, messages, model, url)
            continue

        if user_input == "/index":
            chunks = ingest()
            if not chunks:
                print("No documents found in knowledge/")
                continue
            if not embed_chunks(chunks):
                continue
            save_index(chunks)
            continue
        if user_input.startswith("/rag"):
            question = user_input[len("/rag"):].strip()
            if not question:
                print("Usage: /rag <question>")
                continue
            results = retrieve(question, model, url)
            if results is None:
                continue
            if not results:
                print("Nothing relevant found in the documents")
                continue
            prompt = build_prompt(question, results)
            u_send_message_a(prompt, messages, model, url)
            for chunk in results:
                print(f"Sources: {chunk['source']} - line {chunk['line']} - score {chunk['score']:.2f}")
            continue

        u_send_message_a(user_input, messages, model, url)


if __name__ == "__main__":
    main()
