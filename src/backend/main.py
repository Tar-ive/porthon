import json
import uuid
from pathlib import Path
from typing import Any, List, Optional

import ollama
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

ASSETS_DIR = Path(__file__).parent / "static"


class ClientMessagePart(BaseModel):
    type: str
    text: Optional[str] = None

    model_config = {"extra": "allow"}


class ClientMessage(BaseModel):
    role: str
    content: Optional[str] = None
    parts: Optional[List[ClientMessagePart]] = None

    model_config = {"extra": "allow"}


class ChatRequest(BaseModel):
    messages: List[ClientMessage]

    model_config = {"extra": "allow"}


def extract_text(msg: ClientMessage) -> str:
    if msg.parts:
        return "".join(p.text or "" for p in msg.parts if p.type == "text")
    return msg.content or ""


def format_sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"


OLLAMA_HOST = "http://192.168.1.26:11434"
OLLAMA_MODEL = "qwen3:8b"


def stream_chat(messages: List[ClientMessage]):
    client = ollama.Client(host=OLLAMA_HOST)
    ollama_messages = [{"role": m.role, "content": extract_text(m)} for m in messages]

    message_id = f"msg-{uuid.uuid4().hex}"
    yield format_sse({"type": "start", "messageId": message_id})

    text_stream_id = "text-1"
    text_started = False

    for chunk in client.chat(model=OLLAMA_MODEL, messages=ollama_messages, stream=True):
        delta = chunk.message.content or ""
        if delta:
            if not text_started:
                yield format_sse({"type": "text-start", "id": text_stream_id})
                text_started = True
            yield format_sse({"type": "text-delta", "id": text_stream_id, "delta": delta})

    if text_started:
        yield format_sse({"type": "text-end", "id": text_stream_id})

    yield format_sse({"type": "finish"})
    yield "data: [DONE]\n\n"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat")
async def handle_chat(request: ChatRequest):
    response = StreamingResponse(
        stream_chat(request.messages),
        media_type="text/event-stream",
    )
    response.headers["x-vercel-ai-ui-message-stream"] = "v1"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    return response


# Serve the Vite SPA — html=True handles client-side routing (returns index.html for unknown paths)
if ASSETS_DIR.exists():
    app.mount("/", StaticFiles(directory=ASSETS_DIR, html=True), name="spa")
