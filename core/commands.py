from core.llm import chat

KNOWN_COMMANDS = ["/help", "/clear", "/undo", "/retry", "/code", "/internet_search", "/index", "/rag", "/fast"]

HELP_TEXT = """Commands:
  /help                     show this list
  /clear                    start a new conversation
  /undo                     remove the last question and answer
  /retry                    generate a new answer to the last question
  /code <task>              write, run and fix Python code
  /internet_search <query>  search the web
  /index                    index the documents in knowledge/
  /rag <question>           answer from the documents
  /fast <seconds> <task>    run a task within a time budget
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

def handle_command(user_input, messages, model, url):
    command = user_input.strip()
    if command == "/help":
        return HELP_TEXT
    if command == "/clear":
        return clear(messages)
    if command == "/undo":
        return undo(messages)
    if command == "/retry":
        return retry(messages, model, url)
    if command.startswith("/") and command.split()[0] not in KNOWN_COMMANDS:
        return "Unknown command, type /help"
    return None
