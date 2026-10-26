import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from core.llm import chat
from core.persona import load_persona, build_system_prompt
from core.commands import handle_command

HOST = "127.0.0.1"
PORT = 4040
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

@app.post("/api/chat")
def api_chat(request: ChatRequest):
    output = handle_command(request.text, messages, MODEL, OLLAMA_URL)
    if output is None:
        messages.append({"role": "user", "content": request.text})
        reply = chat(messages, MODEL, OLLAMA_URL)
        if reply is None:
            messages.pop()
            output = "Sensai could not answer (is Ollama running?)"
        else:
            messages.append({"role": "assistant", "content": reply})
    return {"output": output, "messages": messages[1:]}

def run(model, url, persona):
    global MODEL, OLLAMA_URL

    MODEL = model
    OLLAMA_URL = url
    messages[0] = build_system_prompt(load_persona(persona))
    uvicorn.run(app, host=HOST, port=PORT)
