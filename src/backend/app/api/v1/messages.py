"""POST /v1/messages — Chat with SSE streaming (renamed from /api/chat)."""

from __future__ import annotations

import logging
import os
from typing import List

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth import get_mode
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


class ActionRef(BaseModel):
    id: str
    action: str
    title: str | None = None
    data_ref: str
    pattern_id: str | None = None
    rationale: str
    compound_summary: str

    model_config = {"extra": "allow"}


class CreateMessageRequest(BaseModel):
    messages: List[ClientMessage]
    scenario: ScenarioRef | None = None
    actions: List[ActionRef] = []

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
    mode = get_mode(request.headers.get("Authorization"))

    try:
        from deepagent.workers.kg_worker import KgWorker
        kg = KgWorker()
        kg_payload: dict = {"query": last_user_text}

        if mode == "demo":
            # Use demo snippets — no external services needed
            kg_payload["demo_mode"] = True
        else:
            # Live mode: lazily init LightRAG if not already running
            import main as main_mod
            if main_mod._rag is None:
                from deepagent.workers.kg_worker import _create_rag_instance
                rag = _create_rag_instance()
                if rag is not None:
                    await rag.initialize_storages()
                    main_mod._rag = rag

        result = await kg._search(kg_payload)
        if result.ok and result.data:
            raw = result.data.get("raw_context")
            snippets = result.data.get("snippets", [])
            if raw:
                context = raw
            elif snippets:
                context = "\n\n".join(snippets)
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

    actions_context = None
    if body.actions:
        lines = []
        for i, a in enumerate(body.actions, 1):
            label = a.title or a.action
            lines.append(f"{i:02d}. {label}")
            lines.append(f"    Rationale: {a.rationale}")
            if a.data_ref:
                lines.append(f"    Grounded in: {a.data_ref}")
        actions_context = "\n".join(lines)

    system_prompt = build_system_prompt(context=context, intent=intent, scenario=scenario_context, actions=actions_context)

    events = (
        iter_openai_events(body.messages, model=OPENAI_MODEL, system_prompt=system_prompt)
        if USE_OPENAI
        else iter_ollama_events(body.messages, host=OLLAMA_HOST, model=OLLAMA_MODEL, system_prompt=system_prompt)
    )
    response = StreamingResponse(wrap_stream(events), media_type="text/event-stream")
    response.headers["x-porthon-intent"] = intent
    return patch_response_with_headers(response)
