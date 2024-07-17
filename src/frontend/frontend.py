import requests
import logging
from fastapi import FastAPI, Body, Request, Response
from fastapi.responses import PlainTextResponse, HTMLResponse, FileResponse

frontend = FastAPI()
logger = logging.getLogger("uvicorn")

@frontend.get("/", response_class=HTMLResponse)
async def index():
    return open("index.html").read()

@frontend.get("/index.js")
def get_js():
    return FileResponse(f"index.js")

@frontend.get("/index.css")
def get_css():
    return FileResponse(f"index.css")

@frontend.post("/search", response_class=Response)
def handle_search(data=Body(...)):
    return requests.post("http://sort/search", data=data).content

@frontend.post("/data", response_class=Response)
def add_data(data=Body(...)):
    return requests.post("http://sort/data", data=data).content

@frontend.post("/train", response_class=Response)
def add_data(data=Body(...)):
    return requests.post("http://sort/train", data=data).content
