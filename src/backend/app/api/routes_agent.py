"""Always-on agent runtime routes."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth import get_livemode, get_mode
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

    master = get_master(request)
    return await get_runtime(request=request, master=master)


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
    from app.deps import get_master

    master = get_master(request)
    mode = get_mode(request.headers.get("Authorization"))
    from integrations.composio_client import set_demo_mode

    set_demo_mode(mode == "demo")

    try:
        if mode == "demo":
            from pipeline.demo_theo import (
                generate_demo_actions,
                generate_demo_scenarios,
                normalize_demo_scenario_id,
            )

            scenario_id = normalize_demo_scenario_id(body.scenario_id)

            scenarios = generate_demo_scenarios("p05")
            chosen = next(
                (s for s in scenarios if s.get("id") == scenario_id),
                {
                    "id": scenario_id,
                    "title": body.scenario_title or "Quest",
                    "summary": body.scenario_summary,
                    "horizon": body.scenario_horizon or "1yr",
                    "likelihood": body.scenario_likelihood or "possible",
                    "tags": body.scenario_tags or [],
                },
            )
            _ = generate_demo_actions(chosen.get("id", scenario_id), "p05")
        else:
            from pipeline.extractor import extract_persona_data
            from pipeline.scenario_gen import generate_scenarios as generate_scenarios_llm
            from pipeline.action_planner import generate_actions

            extracted = extract_persona_data("p05")
            scenarios = await generate_scenarios_llm(extracted)
            chosen = next(
                (s for s in scenarios if s.get("id") == body.scenario_id),
                {
                    "id": body.scenario_id,
                    "title": body.scenario_title or "Quest",
                    "summary": body.scenario_summary,
                    "horizon": body.scenario_horizon or "1yr",
                    "likelihood": body.scenario_likelihood or "possible",
                    "tags": body.scenario_tags or [],
                },
            )
            await generate_actions(chosen, extracted)
        result = await master.activate_scenario(
            scenario=chosen, demo_mode=(mode == "demo")
        )
        return result
    except Exception as e:
        from app.middleware.errors import ApiException

        raise ApiException(status_code=500, code="internal_error", message=str(e))


@router.post("/events", include_in_schema=False)
async def post_agent_event(body: AgentEventRequest, request: Request):
    from app.api.v1.events import CreateEventRequest
    from app.deps import get_master

    mode = get_mode(request.headers.get("Authorization"))
    from integrations.composio_client import set_demo_mode

    set_demo_mode(mode == "demo")
    payload = dict(body.payload or {})
    if mode == "demo":
        if body.type.startswith("demo.workflow."):
            payload.setdefault("demo_mode", True)
        if payload.get("enqueue"):
            task_payload = dict(payload.get("task_payload") or {})
            task_payload.setdefault("demo_mode", True)
            payload["task_payload"] = task_payload
    event_req = CreateEventRequest(type=body.type, payload=payload)
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
        "livemode": get_livemode(request.headers.get("Authorization")),
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


# ---------------------------------------------------------------------------
# Demo feed — scripted real-time data events
# ---------------------------------------------------------------------------

_DEMO_FEED_DIR = Path(__file__).resolve().parents[4] / "data" / "demo_feed"
_PERSONA_DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "all_personas" / "persona_p05"


def _load_demo_events() -> list[dict]:
    if not _DEMO_FEED_DIR.exists():
        return []
    events = []
    for f in sorted(_DEMO_FEED_DIR.glob("*.json")):
        try:
            import json as _json
            events.append(_json.loads(f.read_text()))
        except Exception:
            pass
    return events


@router.get("/demo/events", include_in_schema=False)
async def list_demo_events():
    """List available scripted demo feed events."""
    events = _load_demo_events()
    return {
        "events": [
            {
                "slug": e["slug"],
                "label": e["label"],
                "description": e["description"],
                "domain": e["domain"],
            }
            for e in events
        ]
    }


@router.post("/demo/push/{slug}", include_in_schema=False)
async def push_demo_event(slug: str, request: Request):
    """Append a scripted record to Theo's data files and trigger immediate re-analysis."""
    import json as _json

    event_file = _DEMO_FEED_DIR / f"{slug}.json"
    if not event_file.exists():
        from app.middleware.errors import ApiException
        raise ApiException(
            status_code=404,
            code="resource_missing",
            message=f"Demo event '{slug}' not found.",
            param="slug",
        )

    descriptor = _json.loads(event_file.read_text())
    record = descriptor["record"]
    target_file = _PERSONA_DATA_DIR / descriptor["file"]

    # Append the new JSONL record
    with target_file.open("a") as fh:
        fh.write(_json.dumps(record) + "\n")

    # Trigger immediate DataWatcher check (don't wait for 3s poll)
    watcher = getattr(request.app.state, "data_watcher", None)
    if watcher is not None:
        asyncio.create_task(watcher.force_check())

    return {
        "ok": True,
        "slug": slug,
        "label": descriptor["label"],
        "domain": descriptor["domain"],
        "record_id": record["id"],
        "file": descriptor["file"],
    }
