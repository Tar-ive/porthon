"""GET /v1/health"""

from __future__ import annotations

import os

from fastapi import APIRouter, Request

from app.auth import get_livemode

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    rag = (
        getattr(request.app.state, "_rag", None)
        if hasattr(request.app.state, "_rag")
        else None
    )
    # Check for rag on the module-level variable via app
    try:
        from main import _rag

        rag_ok = _rag is not None
    except Exception:
        rag_ok = False

    livemode = get_livemode(request.headers.get("Authorization"))

    return {
        "object": "health",
        "status": "ok",
        "backend": "openai" if os.environ.get("OPENAI_API_KEY") else "ollama",
        "rag": rag_ok,
        "livemode": livemode,
    }
