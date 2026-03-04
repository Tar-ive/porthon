"""FastAPI dependency helpers for deep-agent runtime."""

from __future__ import annotations

from fastapi import HTTPException, Request

from deepagent.loop import AlwaysOnMaster


def get_master(request: Request) -> AlwaysOnMaster:
    master = getattr(request.app.state, "always_on_master", None)
    if master is None:
        raise HTTPException(status_code=503, detail="Always-on master not initialized")
    return master
