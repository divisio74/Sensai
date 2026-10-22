import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from core.llm import chat
from core.persona import load_persona, build_system_prompt

HOST = "127.0.0.1"
PORT = 4040
MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://localhost:11434/api/chat"

system_message = build_system_prompt(load_persona("sensia"))

app = FastAPI()

class ChatRequest(BaseModel):
    messages: list

@app.get("/")
def home():
    return FileResponse("web/index.html")

@app.get("/css/style.css")
def style():
    return FileResponse("web/css/style.css")

@app.get("/js/app.js")
def script():
    return FileResponse("web/js/app.js")

@app.post("/api/chat")
def api_chat(request: ChatRequest):
    reply = chat([system_message] + request.messages, MODEL, OLLAMA_URL)
    if reply is None:
        return {"error": "Sensai could not answer (is Ollama running?)"}
    return {"reply": reply}

def run():
    uvicorn.run(app, host=HOST, port=PORT)

if __name__ == "__main__":
    run()