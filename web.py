import uvicorn
import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from core.config import CONFIG
from core.llm import stream_chat
from core.persona import load_persona, build_system_prompt
from core.commands import handle_command

HOST = CONFIG["web"]["host"]
PORT = CONFIG["web"]["port"]
MODEL = None
OLLAMA_URL = None

messages = [build_system_prompt(load_persona("sensia"))]

app = FastAPI()

class ChatRequest(BaseModel):
    text: str

@app.get("/")
def home():
    return FileResponse("web/index.html")

@app.get("/css/style.css")
def style():
    return FileResponse("web/css/style.css")

@app.get("/js/app.js")
def script():
    return FileResponse("web/js/app.js")

@app.get("/api/history")
def api_history():
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
    output = handle_command(request.text, messages, MODEL, OLLAMA_URL)
    if output is not None:
        return {"output": output, "messages": messages[1:]}
    return StreamingResponse(stream_answer(request.text), media_type="text/plain")

def run(model, url, persona):
    global MODEL, OLLAMA_URL

    MODEL = model
    OLLAMA_URL = url
    messages[0] = build_system_prompt(load_persona(persona))
    uvicorn.run(app, host=HOST, port=PORT)
