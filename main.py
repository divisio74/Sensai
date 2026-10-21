import argparse
import json
import requests
from dotenv import load_dotenv

from core.llm import chat
from core.boucle import code_cycle
from core.persona import PERSONAS_DIR, load_persona, build_system_prompt
from rag.ingest import ingest
from tools.internet_search import internet_search
from rag.embed import embed_chunks
from rag.store import save_index
from rag.retrieve import retrieve, build_prompt
from timepred.runner import run as run_timed
from core.commands import handle_command



MAX_SEARCH_ROUNDS = 3
MAX_FAST_RUNS = 1


def parse_json_reply(reply):
    clean_reply = reply.strip("` \n")
    if clean_reply.startswith("json"):
        clean_reply = clean_reply[4:].strip()
    try:
        return json.loads(clean_reply)
    except ValueError:
        return None


def fast_request(parsed):
    if not isinstance(parsed, dict) or parsed.get("tool") != "fast":
        return None
    task = parsed.get("task")
    try:
        seconds = float(parsed.get("seconds"))
    except (TypeError, ValueError):
        return None
    if not isinstance(task, str) or not task.strip() or seconds <= 0:
        return None
    return task.strip(), seconds


def run_fast(task, budget, model, url, persona):
    try:
        return run_timed(task, model, url, budget, allow_direct=persona != "dev")
    except (requests.exceptions.RequestException, ValueError, KeyError) as e:
        print(f"Timed run failed: {e}")
    except KeyboardInterrupt:
        print("\n[fast mode interrupted]")
    return None


def fast_note(summary, persona):
    note = (f"[fast mode] This task actually took {summary['elapsed']:.0f} seconds "
            f"(the user's time budget was {summary['budget']:.0f}s, "
            f"the prediction was {summary['predicted']:.0f}s)")
    if summary["removed"]:
        note += f", dropped steps: {', '.join(summary['removed'])}"
    if summary["code_verified"] is True:
        note += ". Its code was actually run in a sandbox and worked"
    elif summary["code_verified"] is False:
        note += ". Its code could NOT be verified: at least one code step failed"
    elif persona == "dev":
        note += ". No code was executed during this task: nothing was verified"
    if summary["status"] == "stopped":
        note += (". The user stopped the task before the end because the budget would be "
                 "exceeded: the result below is INCOMPLETE")
    return f"{note}\n\n{summary['result']}"


def run_requested_fast(task, seconds, model, url, persona):
    print(f"\n[Sensia wants to run: /fast {seconds:.0f} {task}]")
    try:
        answer = input("Run it? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = ""
    if answer != "y":
        return "The user declined the fast run. Do not request it again unless asked."
    summary = run_fast(task, seconds, model, url, persona)
    if summary is None:
        return "The fast run failed or was interrupted."
    if summary["status"] == "cancelled":
        return "The fast run was cancelled: the time budget is too small for this task."
    return f"Result of the fast run:\n{fast_note(summary, persona)}\nNow answer the user."


def u_send_message_a(content, messages, model, url, persona):
    messages.append({"role": "user", "content": content})
    search_rounds, fast_runs = 0, 0
    while True:
        print("Sensia: ", end="", flush=True)
        reply = chat(messages, model, url)
        if reply is None:
            messages.pop()
            return
        messages.append({"role": "assistant", "content": reply})
        parsed = parse_json_reply(reply)

        request = fast_request(parsed)
        if request:
            fast_runs += 1
            if fast_runs > MAX_FAST_RUNS:
                print("\n[Only one fast run per message, stopping]")
                break
            task, seconds = request
            result = run_requested_fast(task, seconds, model, url, persona)
            messages.append({"role": "user", "content": result})
            continue

        try:
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
    parser.add_argument("--persona", default="sensia", help="persona file in persona/personas/")
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
    persona = args.persona

    try:
        persona_text = load_persona(persona)
    except FileNotFoundError:
        available = ", ".join(sorted(path.stem for path in PERSONAS_DIR.glob("*.md")))
        print(f"Unknown persona '{persona}'. Available: {available}")
        return
    if not check_ollama(model, url):
        return
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

        if handle_command(user_input, messages, model, url):
            continue

        if user_input.startswith("/code "):
            task = user_input[len("/code "):]
            if not task.strip():
                print("Usage: /code <task>")
                continue
            cc_output = code_cycle(task, model, url)
            if cc_output["status"] == "success":
                content = "Here is the code you need :" + cc_output["code"] + "and the result of his execution :" + cc_output["stdout"]
                u_send_message_a(content, messages, model, url, persona)
                continue
            else:
                content = "Unfortunetely its impossible to do this actually ask me to remake my goals !"
                u_send_message_a(content, messages, model, url, persona)
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
            summary = run_fast(task, budget, model, url, persona)
            if summary is None or summary["status"] == "cancelled":
                continue
            messages.append({"role": "user", "content": task})
            messages.append({"role": "assistant", "content": fast_note(summary, persona)})
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
            u_send_message_a(query + "\n find the best answer among these results:\n" + results, messages, model, url, persona)
            continue

        if user_input == "/index":
            chunks = ingest()
            if not chunks:
                print("No documents found in knowledge/documents/")
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
            u_send_message_a(prompt, messages, model, url, persona)
            for chunk in results:
                print(f"Sources: {chunk['source']} - line {chunk['line']} - score {chunk['score']:.2f}")
            continue

        u_send_message_a(user_input, messages, model, url, persona)


if __name__ == "__main__":
    main()
