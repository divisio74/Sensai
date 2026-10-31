import json

from core.llm import chat
from rag.ingest import ingest
from rag.embed import embed_chunks
from rag.store import save_index
from rag.retrieve import retrieve, build_prompt
from core.boucle import code_cycle
from core.persona import load_persona, build_system_prompt, list_personas, get_persona_name, load_user_profile, remember
from core.auth import profile_path

KNOWN_COMMANDS = ["/help", "/clear", "/undo", "/retry", "/code", "/index", "/rag", "/fast", "/persona", "/remember"]

HELP_TEXT = """Commands:
  /help                     show this list
  /clear                    start a new conversation
  /undo                     remove the last question and answer
  /retry                    generate a new answer to the last question
  /code <task>              write, run and fix Python code
  /index                    index the documents in knowledge/
  /rag <question>           answer from the documents
  /fast <seconds> <task>    run a task within a time budget
  /persona <name>           switch persona, the conversation is kept
  /remember <fact>          save a fact in your profile
  quit                      exit Sensia"""

def clear(messages):
    del messages[1:]
    return "Conversation cleared."

def undo(messages):
    if len(messages) <= 1:
        return "Nothing to undo."
    if messages[-1]["role"] == "assistant":
        messages.pop()
    if len(messages) > 1 and messages[-1]["role"] == "user":
        messages.pop()
    return "Last exchange removed."

def retry(messages, model, url):
    if len(messages) <= 1 or messages[-1]["role"] != "assistant":
        return "Nothing to retry."
    old_reply = messages.pop()
    print("Sensia: ", end="", flush=True)
    reply = chat(messages, model, url)
    if reply is None:
        messages.append(old_reply)
        return "Retry failed, the previous answer was kept."
    messages.append({"role": "assistant", "content": reply})
    return ""

def index_documents():
    chunks = ingest()
    if not chunks:
        return "No documents found in knowledge/documents/"
    if not embed_chunks(chunks):
        return "Indexing failed (is Ollama running?)"
    save_index(chunks)
    return f"{len(chunks)} chunks indexed."

def rag(question, messages, model, url):
    if not question:
        return "Usage: /rag <question>"
    results = retrieve(question, model, url)
    if results is None:
        return "No index found (run /index first) or Ollama is not reachable."
    if not results:
        return "Nothing relevant found in the documents"
    prompt = build_prompt(question, results)
    messages.append({"role": "user", "content": prompt, "display": "/rag " + question})
    print("Sensia: ", end="", flush=True)
    reply = chat(messages, model, url, usage="rag")
    if reply is None:
        messages.pop()
        return "Sensia could not answer (is Ollama running?)"
    messages.append({"role": "assistant", "content": reply})
    messages[-2]["content"] = question
    sources = ""
    for chunk in results:
        sources += f"\nSources: {chunk['source']} - line {chunk['line']} - score {chunk['score']:.2f}"
    return sources

def format_attempts(attempts):
    text = ""
    for number, attempt in enumerate(attempts, 1):
        text += f"Attempt {number}:\n```python\n{attempt['code']}\n```\n"
        if attempt["error"]:
            text += f"Error:\n```\n{attempt['error'][-500:]}\n```\n"
    return text

def code(task, messages, model, url):
    if not task:
        return "Usage: /code <task>"
    result = code_cycle(task, model, url)
    if result["status"] == "success":
                content = ("Here is the code that was run:\n```python\n" + result["code"] + "\n```\n"
                   + "Its output:\n" + (result["stdout"] or "(nothing printed)") + "\n"
                   + "Explain this code to the user in a few sentences.")
    else:
        content = "Unfortunetely its impossible to do this actually ask me to remake my goals !"
    messages.append({"role": "user", "content": content, "display": "/code " + task})
    print("Sensia: ", end="", flush=True)
    reply = chat(messages, model, url)
    if reply is None:
        messages.pop()
        return "Sensia could not answer (is Ollama running?)"
    attempts = format_attempts(result["attempts"])
    if result["status"] == "success":
        reply = attempts + "Output:\n```\n" + result["stdout"] + "```\n" + reply
    else:
        reply = attempts + reply
    messages.append({"role": "assistant", "content": reply})
    return ""

def refresh_prompt(messages, user):
    profile = load_user_profile(profile_path(user["email"]))
    messages[0] = build_system_prompt(load_persona(user["persona"]), profile)

def switch_persona(name, messages, user):
    if name not in list_personas():
        return f"Current persona: {user['persona']}. Available: {', '.join(list_personas())}"
    user["persona"] = name
    refresh_prompt(messages, user)
    return f"Switched to {get_persona_name(name)} (conversation kept)"

def remember_fact(fact, messages, user):
    if not fact:
        return "Usage: /remember <fact>"
    remember(fact, profile_path(user["email"]))
    refresh_prompt(messages, user)
    return "Fact remembered."

def handle_command(user_input, messages, model, url, user):
    command = user_input.strip()
    if command == "/help":
        return HELP_TEXT
    if command == "/clear":
        return clear(messages)
    if command == "/undo":
        return undo(messages)
    if command == "/retry":
        return retry(messages, model, url)
    if command == "/index":
        return index_documents()
    if command.startswith("/rag"):
        return rag(command[len("/rag"):].strip(), messages, model, url)
    if command.startswith("/code"):
        return code(command[len("/code"):].strip(), messages, model, url)
    if command == "/persona" or command.startswith("/persona "):
        return switch_persona(command[len("/persona"):].strip(), messages, user)
    if command == "/remember" or command.startswith("/remember "):
        return remember_fact(command[len("/remember"):].strip(), messages, user)
    if command.startswith("/") and command.split()[0] not in KNOWN_COMMANDS:
        return "Unknown command, type /help"
    return None
