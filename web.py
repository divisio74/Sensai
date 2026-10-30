import uvicorn
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from core.config import CONFIG
from core.llm import stream_chat
from core.persona import load_persona, build_system_prompt, list_personas, load_user_profile
from core.commands import handle_command
from core.auth import login, register, profile_path

HOST = CONFIG["web"]["host"]
PORT = CONFIG["web"]["port"]
MODEL = None
OLLAMA_URL = None
CURRENT_USER = None

messages = [build_system_prompt(load_persona("sensia"))]

app = FastAPI()

class ChatRequest(BaseModel):
    text: str

class LoginRequest(BaseModel):
    email: str
    password: str
    persona: str = "sensia"
    about: str = ""

def check_logged_in():
    if CURRENT_USER is None:
        raise HTTPException(status_code=401, detail="Not logged in.")

def start_session(user):
    global CURRENT_USER

    CURRENT_USER = user
    profile = load_user_profile(profile_path(user["email"]))
    messages[:] = [build_system_prompt(load_persona(user["persona"]), profile)]

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
    return {"messages": messages[1:]}

def stream_answer(text):
    messages.append({"role": "user", "content": text})
    reply = ""
    try:
        for piece in stream_chat(messages, MODEL, OLLAMA_URL):
            reply += piece
            yield piece
    except requests.exceptions.RequestException:
        messages.pop()
        yield "\n[Sensai could not answer (is Ollama running?)]"
        return
    messages.append({"role": "assistant", "content": reply})

@app.post("/api/chat")
def api_chat(request: ChatRequest):
    check_logged_in()
    output = handle_command(request.text, messages, MODEL, OLLAMA_URL, CURRENT_USER)
    if output is not None:
        return {"output": output, "messages": messages[1:]}
    return StreamingResponse(stream_answer(request.text), media_type="text/plain")

def run(model, url, persona):
    global MODEL, OLLAMA_URL

    MODEL = model
    OLLAMA_URL = url
    messages[0] = build_system_prompt(load_persona(persona))
    uvicorn.run(app, host=HOST, port=PORT)
