import uvicorn
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from core.config import CONFIG
from core.llm import stream_messages, LAST_USAGE
from core.mcp_client import get_tools, call_tool
from core.persona import load_persona, build_system_prompt, list_personas, load_user_profile
from core.commands import handle_command
from core.auth import login, register, profile_path
from core.history import load_history, save_history

HOST = CONFIG["web"]["host"]
PORT = CONFIG["web"]["port"]
MODEL = None
OLLAMA_URL = None
CURRENT_USER = None
MAX_TOOL_ROUNDS = CONFIG["chat"]["max_tool_rounds"]
TOOLS = []

messages = [build_system_prompt(load_persona("sensia"))]

app = FastAPI()

class ChatRequest(BaseModel):
    text: str

class LoginRequest(BaseModel):
    email: str
    password: str
    persona: str = "sensia"
    about: str = ""

def context_usage():
    used = LAST_USAGE["prompt"] + LAST_USAGE["answer"]
    if used == 0:
        for message in messages:
            used += len(message["content"])
        used = used // 4
    if len(messages) == 1:
        used = 0
    return {"used": used, "max": CONFIG["generation"]["num_ctx"]}

def check_logged_in():
    if CURRENT_USER is None:
        raise HTTPException(status_code=401, detail="Not logged in.")

def start_session(user):
    global CURRENT_USER

    CURRENT_USER = user
    LAST_USAGE["prompt"] = 0
    LAST_USAGE["answer"] = 0
    profile = load_user_profile(profile_path(user["email"]))
    messages[:] = [build_system_prompt(load_persona(user["persona"]), profile)] + load_history(user["email"])

@app.get("/")
def home():
    page = "web/login.html" if CURRENT_USER is None else "web/index.html"
    return FileResponse(page, headers={"Cache-Control": "no-store"})

@app.get("/css/style.css")
def style():
    return FileResponse("web/css/style.css")

@app.get("/js/app.js")
def script():
    return FileResponse("web/js/app.js")

@app.get("/js/login.js")
def login_script():
    return FileResponse("web/js/login.js")

@app.get("/api/personas")
def api_personas():
    return {"personas": list_personas()}

@app.post("/api/login")
def api_login(request: LoginRequest):
    user = login(request.email.strip(), request.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Wrong email or password.")
    start_session(user)
    return {"ok": True}

@app.post("/api/register")
def api_register(request: LoginRequest):
    if request.persona not in list_personas():
        raise HTTPException(status_code=400, detail="Unknown persona.")
    email = request.email.strip()
    error = register(email, request.password, request.persona, request.about)
    if error:
        raise HTTPException(status_code=400, detail=error)
    start_session({"email": email, "persona": request.persona})
    return {"ok": True}

@app.post("/api/logout")
def api_logout():
    global CURRENT_USER
    CURRENT_USER = None
    messages[:] = [build_system_prompt(load_persona("sensia"))]
    return {"ok": True}

@app.get("/api/history")
def api_history():
    check_logged_in()
    return {"messages": messages[1:], "context": context_usage()}


def stream_answer(text):
    start = len(messages)
    messages.append({"role": "user", "content": text})
    for _ in range(MAX_TOOL_ROUNDS + 1):
        reply, tool_calls = "", []
        try:
            for message in stream_messages(messages, MODEL, OLLAMA_URL, TOOLS):
                reply += message["content"]
                tool_calls.extend(message.get("tool_calls") or [])
                yield message["content"]
        except requests.exceptions.RequestException:
            del messages[start:]
            yield "\n[Sensai could not answer (is Ollama running?)]"
            return
        assistant = {"role": "assistant", "content": reply}
        if tool_calls:
            assistant["tool_calls"] = tool_calls
        messages.append(assistant)
        if not tool_calls:
            return
        for call in tool_calls:
            name = call["function"]["name"]
            arguments = call["function"]["arguments"]
            yield f"\n[Tool {name}: {arguments}]\n"
            try:
                output = call_tool(name, arguments)
            except Exception as e:
                output = f"Error calling '{name}': {e}"
            messages.append({"role": "tool", "tool_name": name, "content": output})
    yield "\n[Too many tool calls, stopping]"

def stream_and_save(text):
    yield from stream_answer(text)
    save_history(CURRENT_USER["email"], messages)

@app.post("/api/chat")
def api_chat(request: ChatRequest):
    check_logged_in()
    output = handle_command(request.text, messages, MODEL, OLLAMA_URL, CURRENT_USER)
    if output is not None:
        save_history(CURRENT_USER["email"], messages)
        return {"output": output, "messages": messages[1:], "context": context_usage()}
    return StreamingResponse(stream_and_save(request.text), media_type="text/plain")

def run(model, url, persona):
    global MODEL, OLLAMA_URL

    MODEL = model
    OLLAMA_URL = url
    messages[0] = build_system_prompt(load_persona(persona))
    try:
        TOOLS.extend(get_tools())
    except Exception as e:
        print(f"MCP server unavailable, continuing without tools: {e}")
    uvicorn.run(app, host=HOST, port=PORT)
