"""Always-on agent runtime routes."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.deps import get_master
from deepagent.loop import AlwaysOnMaster
from deepagent.skills.registry import SKILL_REGISTRY

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentEventRequest(BaseModel):
    type: str
    payload: dict[str, Any] = {}


class ActivateAgentRequest(BaseModel):
    scenario_id: str
    scenario_title: str
    scenario_summary: str
    scenario_horizon: str
    scenario_likelihood: str
    scenario_tags: list[str] = []


class ApprovalDecisionRequest(BaseModel):
    approval_id: str
    decision: str


@router.get("/state")
async def get_agent_state(master: AlwaysOnMaster = Depends(get_master)):
    return await master.get_state()


@router.get("/map")
async def get_agent_map(master: AlwaysOnMaster = Depends(get_master)):
    return await master.get_map()


@router.get("/skills")
async def get_skills():
    return {"skills": [skill.model_dump(mode="json") for skill in SKILL_REGISTRY]}


@router.post("/activate")
async def activate_agent(request: ActivateAgentRequest, master: AlwaysOnMaster = Depends(get_master)):
    return await master.activate_scenario(
        {
            "id": request.scenario_id,
            "title": request.scenario_title,
            "summary": request.scenario_summary,
            "horizon": request.scenario_horizon,
            "likelihood": request.scenario_likelihood,
            "tags": request.scenario_tags,
        }
    )


@router.post("/events")
async def post_agent_event(request: AgentEventRequest, master: AlwaysOnMaster = Depends(get_master)):
    return await master.ingest_event(request.type, request.payload)


@router.post("/approve")
async def resolve_approval(request: ApprovalDecisionRequest, master: AlwaysOnMaster = Depends(get_master)):
    return await master.resolve_approval(request.approval_id, request.decision)


@router.get("/stream")
async def stream_agent_events(master: AlwaysOnMaster = Depends(get_master)):
    sid, queue = master.stream.subscribe()

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {json.dumps(event)}\\n\\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\\n\\n"
        finally:
            master.stream.unsubscribe(sid)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
