import asyncio
import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from simulation.scenarios import generate_scenarios
from utils import (
    ClientMessage,
    ClientMessagePart,  # noqa: F401 — re-exported for Pydantic schema discovery
    iter_ollama_events,
    iter_openai_events,
    patch_response_with_headers,
    wrap_stream,
)
from pydantic import BaseModel

load_dotenv()

app = FastAPI()

ASSETS_DIR = Path(__file__).parent / "static"

OLLAMA_HOST = "http://192.168.1.26:11434"
OLLAMA_MODEL = "qwen3:8b"
OPENAI_MODEL = "gpt-4o-mini"

USE_OPENAI = bool(os.environ.get("OPENAI_API_KEY"))


class ChatRequest(BaseModel):
    messages: List[ClientMessage]

    model_config = {"extra": "allow"}


@app.get("/api/health")
def health():
    return {"status": "ok", "backend": "openai" if USE_OPENAI else "ollama"}


@app.get("/api/scenarios")
async def get_scenarios():
    await asyncio.sleep(3)  # simulate generation latency
    return generate_scenarios()


@app.post("/api/chat")
async def handle_chat(request: ChatRequest):
    events = (
        iter_openai_events(request.messages, model=OPENAI_MODEL)
        if USE_OPENAI
        else iter_ollama_events(request.messages, host=OLLAMA_HOST, model=OLLAMA_MODEL)
    )
    response = StreamingResponse(wrap_stream(events), media_type="text/event-stream")
    return patch_response_with_headers(response)


# Serve the Vite SPA — html=True handles client-side routing (returns index.html for unknown paths)
if ASSETS_DIR.exists():
    app.mount("/", StaticFiles(directory=ASSETS_DIR, html=True), name="spa")
