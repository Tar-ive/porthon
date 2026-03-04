"""POST /v1/messages — Chat with SSE streaming (renamed from /api/chat)."""

from __future__ import annotations

import logging
import os
from typing import List

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from utils import (
    ClientMessage,
    extract_text,
    iter_ollama_events,
    iter_openai_events,
    patch_response_with_headers,
    wrap_stream,
)

logger = logging.getLogger(__name__)
router = APIRouter()

OLLAMA_HOST = "http://192.168.1.26:11434"
OLLAMA_MODEL = "qwen3:8b"


class ScenarioRef(BaseModel):
    id: str
    title: str
    horizon: str
    likelihood: str
    summary: str


class CreateMessageRequest(BaseModel):
    messages: List[ClientMessage]
    scenario: ScenarioRef | None = None

    model_config = {"extra": "allow"}


@router.post("/messages")
async def create_message(body: CreateMessageRequest, request: Request):
    from deepagent.workers.kg_worker import classify_intent
    from deepagent.persona.prompt_builder import build_system_prompt

    USE_OPENAI = bool(os.environ.get("OPENAI_API_KEY"))
    OPENAI_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    last_user_text = ""
    for msg in reversed(body.messages):
        if msg.role == "user":
            last_user_text = extract_text(msg)
            break

    intent = classify_intent(last_user_text) if last_user_text else "casual"
    context = None

    try:
        from main import _rag
        if _rag is not None:
            from deepagent.workers.kg_worker import KgWorker
            kg = KgWorker()
            result = await kg._search({"query": last_user_text})
            if result.ok and result.data.get("raw_context"):
                context = result.data["raw_context"]
                intent = result.data.get("intent", intent)
    except Exception as e:
        logger.error(f"KG retrieval error: {e}")

    scenario_context = None
    if body.scenario:
        scenario_context = (
            f"The user is exploring the '{body.scenario.title}' scenario "
            f"({body.scenario.horizon}, {body.scenario.likelihood}): "
            f"{body.scenario.summary}"
        )

    system_prompt = build_system_prompt(context=context, intent=intent, scenario=scenario_context)

    events = (
        iter_openai_events(body.messages, model=OPENAI_MODEL, system_prompt=system_prompt)
        if USE_OPENAI
        else iter_ollama_events(body.messages, host=OLLAMA_HOST, model=OLLAMA_MODEL, system_prompt=system_prompt)
    )
    response = StreamingResponse(wrap_stream(events), media_type="text/event-stream")
    response.headers["x-porthon-intent"] = intent
    return patch_response_with_headers(response)
