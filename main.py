import argparse
import json
import requests
from dotenv import load_dotenv

from core.llm import chat_with_tools
from core.mcp_client import get_tools, call_tool
from core.persona import PERSONAS_DIR, load_persona, build_system_prompt, get_persona_name, load_user_profile, remember
from timepred.runner import run as run_timed
from core.commands import handle_command
from web import run


MAX_TOOL_ROUNDS = 3
MAX_FAST_RUNS = 1
TOOLS = []


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
    tool_rounds, fast_runs = 0, 0
    persona_name = get_persona_name(persona)
    while True:
        print(f"{persona_name}: ", end="", flush=True)
        result = chat_with_tools(messages, model, url, TOOLS)
        if result is None:
            messages.pop()
            return
        reply, tool_calls = result
        message = {"role": "assistant", "content": reply}
        if tool_calls:
            message["tool_calls"] = tool_calls
        messages.append(message)

        request = fast_request(parse_json_reply(reply))
        if request:
            fast_runs += 1
            if fast_runs > MAX_FAST_RUNS:
                print("\n[Only one fast run per message, stopping]")
                break
            task, seconds = request
            result = run_requested_fast(task, seconds, model, url, persona)
            messages.append({"role": "user", "content": result})
            continue

        if tool_calls:
            tool_rounds += 1
            if tool_rounds > MAX_TOOL_ROUNDS:
                print("\n[Too many tool calls, stopping]")
                break
            for call in tool_calls:
                name = call["function"]["name"]
                arguments = call["function"]["arguments"]
                print(f"\n[Tool {name}: {arguments}]")
                try:
                    output = call_tool(name, arguments)
                except Exception as e:
                    output = f"Error calling '{name}': {e}"
                messages.append({"role": "tool", "tool_name": name, "content": output})
            continue
        break


def parse_args():
    parser = argparse.ArgumentParser(description="Sensia: Local assistant")
    parser.add_argument("--model", default="qwen2.5:3b", help="Ollama model to use (default: qwen2.5:3b)")
    parser.add_argument("--url", default="http://localhost:11434/api/chat", help="Ollama chat API URL (default: http://localhost:11434/api/chat)")
    parser.add_argument("--persona", default="sensia", help="persona file in persona/personas/")
    parser.add_argument("--web", action="store_true", help="start the web interface instead of the terminal")
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
    if args.web:
        run(model, url, persona)
        return
    try:
        TOOLS.extend(get_tools())
    except Exception as e:
        print(f"MCP server unavailable, continuing without tools: {e}")
    system_message = build_system_prompt(persona_text, load_user_profile())
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

        if user_input.startswith("/remember "):
            fact = user_input[len("/remember "):]
            if not fact.strip():
                print("Usage: /remember <fact>")
                continue
            remember(fact)
            messages[0] = build_system_prompt(load_persona(persona), load_user_profile())
            print("Fact remembered.")
            continue

        output = handle_command(user_input, messages, model, url)
        if output is not None:
            if output:
                print(output)
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
        u_send_message_a(user_input, messages, model, url, persona)


if __name__ == "__main__":
    main()
