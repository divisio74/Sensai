from core.llm import chat

KNOWN_COMMANDS = ["/help", "/clear", "/undo", "/retry", "/code", "/internet_search", "/index", "/rag", "/fast"]

def print_help():
    print("Commands:")
    print("  /help                     show this list")
    print("  /clear                    start a new conversation")
    print("  /undo                     remove the last question and answer")
    print("  /retry                    generate a new answer to the last question")
    print("  /code <task>              write, run and fix Python code")
    print("  /internet_search <query>  search the web")
    print("  /index                    index the documents in knowledge/")
    print("  /rag <question>           answer from the documents")
    print("  quit                      exit Sensia")

def undo(messages):
    if len(messages) <= 1:
        print("Nothing to undo.")
        return
    if messages[-1]["role"] == "assistant":
        messages.pop()
    if len(messages) > 1 and messages[-1]["role"] == "user":
        messages.pop()
    print("Last exchange removed.")

def retry(messages, model, url):
    if len(messages) <= 1 or messages[-1]["role"] != "assistant":
        print("Nothing to retry.")
        return
    old_reply = messages.pop()
    print("Sensia: ", end="", flush=True)
    reply = chat(messages, model, url)
    if reply is None:
        messages.append(old_reply)
        return
    messages.append({"role": "assistant", "content": reply})

def handle_command(user_input, messages, model, url):
    command = user_input.strip()
    if command == "/help":
        print_help()
        return True
    if command == "/clear":
        del messages[1:]
        print("Conversation cleared.")
        return True
    if command == "/undo":
        undo(messages)
        return True
    if command == "/retry":
        retry(messages, model, url)
        return True
    if command.startswith("/") and command.split()[0] not in KNOWN_COMMANDS:
        print("Unknown command, type /help")
        return True
    return False
