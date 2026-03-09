"""POST /v1/voice/transcribe — Stream audio transcription via OpenRouter."""

from __future__ import annotations

import base64
import json
import logging
import os

import httpx
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
router = APIRouter()

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
TRANSCRIBE_MODEL = "google/gemini-2.5-flash-lite"
TRANSCRIBE_PROMPT = (
    "Transcribe this audio exactly as spoken. "
    "Return only the transcribed words with no commentary, formatting, or extra text."
)


async def _stream_openrouter(audio_b64: str, fmt: str, api_key: str):
    """Yield raw SSE lines from OpenRouter chat completions stream."""
    payload = {
        "model": TRANSCRIBE_MODEL,
        "stream": True,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": TRANSCRIBE_PROMPT},
                    {"type": "input_audio", "input_audio": {"data": audio_b64, "format": fmt}},
                ],
            }
        ],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            f"{OPENROUTER_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.environ.get("PUBLIC_URL", "http://localhost:8000"),
            },
            content=json.dumps(payload),
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                yield line


async def _sse_transcribe(audio_b64: str, fmt: str, api_key: str):
    """Re-emit OpenRouter SSE as our own SSE, forwarding only text delta tokens."""
    async for line in _stream_openrouter(audio_b64, fmt, api_key):
        if not line.startswith("data:"):
            continue
        raw = line[5:].strip()
        if raw == "[DONE]":
            yield "data: [DONE]\n\n"
            return
        try:
            chunk = json.loads(raw)
            delta = chunk["choices"][0]["delta"].get("content", "")
            if delta:
                yield f"data: {json.dumps({'token': delta})}\n\n"
        except Exception:
            pass


@router.post("/voice/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...),
    format: str = Form("webm"),
):
    api_key = os.environ.get("LLM_BINDING_API_KEY", "")
    if not api_key:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="LLM_BINDING_API_KEY not configured")

    raw = await audio.read()
    audio_b64 = base64.b64encode(raw).decode()

    return StreamingResponse(
        _sse_transcribe(audio_b64, format, api_key),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
