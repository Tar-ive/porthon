"""Always-on agent runtime routes."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, Request
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
    scenario_title: str = ""
    scenario_summary: str = ""
    scenario_horizon: str = ""
    scenario_likelihood: str = ""
    scenario_tags: list[str] = []


class ApprovalDecisionRequest(BaseModel):
    approval_id: str
    decision: str


@router.get("/state", include_in_schema=False)
async def get_agent_state(request: Request):
    from app.api.v1.runtime import get_runtime
    from app.deps import get_master

    master = get_master(request)
    return await get_runtime(master)


@router.get("/map", include_in_schema=False)
async def get_agent_map(request: Request):
    from app.api.v1.workers import get_worker_map
    from app.deps import get_master

    master = get_master(request)
    return await get_worker_map(master)


@router.get("/skills", include_in_schema=False)
async def get_skills():
    from app.api.v1.workers import get_worker_skills

    return await get_worker_skills()


@router.post("/activate", include_in_schema=False)
async def activate_agent(body: ActivateAgentRequest, request: Request):
    from pipeline.extractor import extract_persona_data
    from pipeline.scenario_gen import generate_scenarios as generate_scenarios_llm
    from pipeline.action_planner import generate_actions
    from app.deps import get_master

    master = get_master(request)

    try:
        extracted = extract_persona_data(
            body.scenario_id.split("_")[0] if "_" in body.scenario_id else "p05"
        )
        scenarios = await generate_scenarios_llm(extracted)
        chosen = next(
            (s for s in scenarios if s.get("id") == body.scenario_id),
            scenarios[0]
            if scenarios
            else {
                "id": body.scenario_id,
                "title": body.scenario_title,
                "summary": body.scenario_summary,
            },
        )
        await generate_actions(chosen, extracted)
        result = await master.activate_scenario(scenario=chosen)
        return result
    except Exception as e:
        from app.middleware.errors import ApiException

        raise ApiException(status_code=500, code="internal_error", message=str(e))


@router.post("/events", include_in_schema=False)
async def post_agent_event(body: AgentEventRequest, request: Request):
    from app.api.v1.events import CreateEventRequest
    from app.deps import get_master

    event_req = CreateEventRequest(type=body.type, payload=body.payload)
    master = get_master(request)
    result = await master.ingest_event(event_req.type, event_req.payload)
    event = result.get("event", {})
    evt_id = event.get("event_id", "")
    if not evt_id.startswith("evt_"):
        from app.api.v1.schemas import generate_id

        evt_id = generate_id("evt_")
    return {
        "id": evt_id,
        "object": "event",
        "created": event.get("created"),
        "livemode": True,
        "metadata": {},
        "type": event.get("type", event_req.type),
        "payload": event.get("payload", event_req.payload),
        "cycle": result.get("cycle"),
    }


@router.post("/approve", include_in_schema=False)
async def resolve_approval(body: ApprovalDecisionRequest, request: Request):
    from app.api.v1.approvals import ResolveApprovalRequest, _find_approval
    from app.deps import get_master

    master = get_master(request)

    # Get the approval from state to find the correct ID
    state = await master.get_state()
    approval = _find_approval(state.get("approvals", []), body.approval_id)
    if approval is None:
        from app.middleware.errors import ApiException

        raise ApiException(
            status_code=404,
            code="resource_missing",
            message="Approval not found.",
            param="approval_id",
        )

    # Use the ID as stored in state
    state_approval_id = approval.get("approval_id", body.approval_id)
    result = await master.resolve_approval(state_approval_id, body.decision)
    if not result.get("ok"):
        err = result.get("error", "Unknown error")
        from app.middleware.errors import ApiException

        raise ApiException(
            status_code=404 if "not found" in err else 400,
            code="resource_missing" if "not found" in err else "invalid_request",
            message=err,
            param="approval_id",
        )
    return {
        "id": body.approval_id,
        "object": "approval",
        "decision": result.get("decision"),
        "cycle": result.get("cycle"),
    }


@router.get("/stream", include_in_schema=False)
async def stream_agent_events(request: Request):
    from app.api.v1.events import stream_events
    from app.deps import get_master

    master = get_master(request)
    return await stream_events(master)
