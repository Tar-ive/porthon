"""Always-on agent runtime routes."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth import get_livemode, get_mode
from app.deps import get_master
from deepagent.loop import AlwaysOnMaster
from deepagent.skills.registry import SKILL_REGISTRY
from integrations.notion_leads_service import get_notion_leads_service

router = APIRouter(prefix="/api/agent", tags=["agent"])
logger = logging.getLogger(__name__)


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


def _demo_event_to_notion_leads(slug: str, descriptor: dict[str, Any]) -> list[dict[str, Any]]:
    record = descriptor.get("record", {})
    record_text = str(record.get("text", "")).strip()
    record_ts = str(record.get("ts", "")).strip()
    default_follow_up = record_ts[:10] if len(record_ts) >= 10 else "2026-03-09"

    mappings: dict[str, list[dict[str, Any]]] = {
        "01_high_value_client": [
            {
                "name": "NovaBit",
                "status": "Meeting booked",
                "lead_type": "Inbound",
                "priority": "High",
                "deal_size": 2700,
                "source": "Direct",
                "next_action": "Send discovery recap and scope options within 48 hours",
                "next_follow_up_date": default_follow_up,
                "notes": f"Questline demo push 01_high_value_client. {record_text}",
                "lead_key": "novabit::direct",
            }
        ],
        "02_debt_milestone": [
            {
                "name": "Freed Capacity Sprint",
                "status": "Lead",
                "lead_type": "Outbound",
                "priority": "High",
                "deal_size": 1000,
                "source": "Direct",
                "next_action": "Convert the freed debt capacity into 3 warm outreach follow-ups this week",
                "next_follow_up_date": default_follow_up,
                "notes": f"Questline demo push 02_debt_milestone. Derived internal revenue sprint from: {record_text}",
                "lead_key": "freed capacity sprint::direct",
            }
        ],
        "03_motion_reel_viral": [
            {
                "name": "Motion Reel Inbound",
                "status": "Lead",
                "lead_type": "Inbound",
                "priority": "High",
                "deal_size": 1800,
                "source": "Social",
                "next_action": "Reply to the 12 inbound DMs with one qualifying message and a portfolio link",
                "next_follow_up_date": default_follow_up,
                "notes": f"Questline demo push 03_motion_reel_viral. {record_text}",
                "lead_key": "motion reel inbound::social",
            }
        ],
        "04_agency_partnership": [
            {
                "name": "ATX Creative Co",
                "status": "Proposal sent",
                "lead_type": "Referral",
                "priority": "High",
                "deal_size": 3000,
                "source": "Referral",
                "next_action": "Model retainer economics and reply with a decision window",
                "next_follow_up_date": default_follow_up,
                "notes": f"Questline demo push 04_agency_partnership. {record_text}",
                "lead_key": "atx creative co::referral",
            }
        ],
    }
    return mappings.get(slug, [])


async def _resolve_demo_notion_workspace(master: AlwaysOnMaster) -> dict[str, Any]:
    from app.api.v1.notion_leads import _resolve_workspace

    return await _resolve_workspace(master=master, payload={}, allow_setup=True)


async def _sync_demo_event_to_notion(master: AlwaysOnMaster, slug: str, descriptor: dict[str, Any]) -> dict[str, Any]:
    leads = _demo_event_to_notion_leads(slug, descriptor)
    if not leads:
        return {"status": "skipped", "reason": "no_mapping", "lead_count": 0}

    service = get_notion_leads_service()
    if not service.is_configured():
        return {"status": "skipped", "reason": "notion_unconfigured", "lead_count": len(leads)}

    try:
        workspace = await _resolve_demo_notion_workspace(master)
        sync = await service.sync_leads(
            data_source_id=str(workspace["data_source_id"]),
            leads=leads,
            strict_reconcile=False,
        )
        await master.update_workflow_key(
            "notion_leads",
            {
                **workspace,
                "last_demo_push_sync_at": descriptor.get("record", {}).get("ts", ""),
            },
        )
        logger.info(
            "DEMO PUSH NOTION SYNC OK slug=%s data_source_id=%s created=%s updated=%s noop=%s",
            slug,
            workspace.get("data_source_id", ""),
            sync.get("counts", {}).get("created", 0),
            sync.get("counts", {}).get("updated", 0),
            sync.get("counts", {}).get("noop", 0),
        )
        return {
            "status": "completed",
            "lead_count": len(leads),
            "database_id": workspace.get("database_id", ""),
            "data_source_id": workspace.get("data_source_id", ""),
            "counts": sync.get("counts", {}),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("DEMO PUSH NOTION SYNC FAILED slug=%s error=%s", slug, exc)
        return {"status": "failed", "reason": str(exc), "lead_count": len(leads)}


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

    master = get_master(request)
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

    # Trigger immediate DataWatcher check (don't wait for 3s poll).
    # demo_mode=True: re-analysis uses demo scenarios/actions, not live LLM/KG.
    # Notion writes and webhook visibility are unaffected.
    watcher = getattr(request.app.state, "data_watcher", None)
    if watcher is not None:
        asyncio.create_task(watcher.force_check(demo_mode=True))

    notion_sync = await _sync_demo_event_to_notion(master, slug, descriptor)

    return {
        "ok": True,
        "slug": slug,
        "label": descriptor["label"],
        "domain": descriptor["domain"],
        "record_id": record["id"],
        "file": descriptor["file"],
        "notion_sync": notion_sync,
    }
