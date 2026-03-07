"""GET /v1/runtime — Agent runtime state (renamed from /api/agent/state)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth import get_mode
from app.deps import get_master
from deepagent.loop import AlwaysOnMaster

router = APIRouter()


@router.get("/runtime")
async def get_runtime(
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
):
    state = await master.get_state()
    if get_mode(request.headers.get("Authorization")) != "demo":
        state.pop("demo_artifacts", None)
        state.pop("value_signals", None)
        state.pop("workflow_state", None)
    state["object"] = "runtime"
    return state
