"""GET /v1/runtime — Agent runtime state (renamed from /api/agent/state)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import get_master
from deepagent.loop import AlwaysOnMaster

router = APIRouter()


@router.get("/runtime")
async def get_runtime(master: AlwaysOnMaster = Depends(get_master)):
    state = await master.get_state()
    state["object"] = "runtime"
    return state
