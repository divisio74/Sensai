import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse

HOST = "127.0.0.1"
PORT = 4040

app = FastAPI()

@app.get("/")
def home():
    return FileResponse("web/index.html")

@app.get("/css/style.css")
def style():
    return FileResponse("web/css/style.css")

@app.get("/js/app.js")
def script():
    return FileResponse("web/js/app.js")

def run():
    uvicorn.run(app, host=HOST, port=PORT)

if __name__ == "__main__":
    run()