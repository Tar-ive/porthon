"""Deterministic Notion leads CRM endpoints."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.api.v1.schemas import ListObject, epoch_now, generate_id, paginate
from app.auth import get_livemode, get_mode
from app.deps import get_master
from app.middleware.errors import ApiException
from deepagent.loop import AlwaysOnMaster
from integrations.notion_leads_service import (
    default_demo_leads,
    get_notion_leads_service,
    normalize_lead_payload,
)

router = APIRouter()


class LeadsSetupRequest(BaseModel):
    parent_page_id: str | None = None
    database_title: str = "Leads"
    data_source_title: str = "Theo Leads"
    database_id: str | None = None
    data_source_id: str | None = None


class LeadsSyncRequest(BaseModel):
    parent_page_id: str | None = None
    database_title: str = "Leads"
    data_source_title: str = "Theo Leads"
    database_id: str | None = None
    data_source_id: str | None = None
    strict_reconcile: bool = True
    leads: list[dict[str, Any]] = Field(default_factory=list)


class LeadsPatchRequest(BaseModel):
    parent_page_id: str | None = None
    database_id: str | None = None
    data_source_id: str | None = None
    name: str | None = None
    status: str | None = None
    lead_type: str | None = None
    priority: str | None = None
    deal_size: float | None = None
    last_contact: str | None = None
    next_action: str | None = None
    next_follow_up_date: str | None = None
    email_handle: str | None = None
    source: str | None = None
    notes: str | None = None


class LeadsRealtimeRequest(BaseModel):
    action: Literal["sync_leads", "upsert_lead", "patch_lead"] = "upsert_lead"
    priority: int = 20
    task_payload: dict[str, Any] = Field(default_factory=dict)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _priority_weight(value: str) -> int:
    mapping = {"high": 3, "medium": 2, "low": 1}
    return mapping.get(str(value).strip().lower(), 0)


def _resolve_parent_page_id(explicit: str | None) -> str | None:
    value = (
        explicit
        or os.environ.get("NOTION_ROOT_PAGE_ID")
        or os.environ.get("NOTION_PARENT_PAGE_ID")
        or ""
    ).strip()
    return value or None


def _apply_view_filters(
    leads: list[dict[str, Any]],
    view: str | None,
    min_deal_size: float,
) -> list[dict[str, Any]]:
    today = datetime.now(UTC).date().isoformat()

    def is_open(status: str) -> bool:
        return status not in {"Won", "Lost"}

    filtered = list(leads)
    if view == "today_followups":
        filtered = [
            l
            for l in filtered
            if is_open(str(l.get("status", "")))
            and str(l.get("next_follow_up_date", "")).strip()
            and str(l.get("next_follow_up_date")) <= today
        ]
        filtered.sort(
            key=lambda x: (
                _priority_weight(str(x.get("priority", ""))),
                float(x.get("deal_size", 0) or 0),
            ),
            reverse=True,
        )
    elif view == "high_value_focus":
        filtered = [
            l
            for l in filtered
            if is_open(str(l.get("status", "")))
            and float(l.get("deal_size", 0) or 0) >= min_deal_size
        ]
        filtered.sort(key=lambda x: float(x.get("deal_size", 0) or 0), reverse=True)
    elif view == "warm_inbound":
        filtered = [
            l
            for l in filtered
            if str(l.get("lead_type", "")) in {"Inbound", "Referral"}
        ]
    elif view == "prospecting":
        filtered = [
            l
            for l in filtered
            if str(l.get("status", "")) == "Lead" and not str(l.get("last_contact", "")).strip()
        ]
    return filtered


async def _resolve_workspace(
    *,
    master: AlwaysOnMaster,
    payload: dict[str, Any],
    allow_setup: bool = True,
) -> dict[str, Any]:
    workflow = await master.get_workflow_key("notion_leads")
    parent_page_id = _resolve_parent_page_id(str(payload.get("parent_page_id", "")).strip() or None)
    database_title = str(payload.get("database_title") or workflow.get("database_title") or "Leads")
    data_source_title = str(payload.get("data_source_title") or workflow.get("data_source_title") or "Theo Leads")
    database_id = str(payload.get("database_id") or workflow.get("database_id") or "").strip() or None
    data_source_id = str(payload.get("data_source_id") or workflow.get("data_source_id") or "").strip() or None

    if database_id and data_source_id:
        return {
            "parent_page_id": parent_page_id,
            "database_id": database_id,
            "data_source_id": data_source_id,
            "database_title": database_title,
            "data_source_title": data_source_title,
            "database_url": str(workflow.get("database_url", "")),
            "schema_version": str(workflow.get("schema_version", "")),
        }

    if not allow_setup:
        raise ApiException(
            status_code=400,
            code="invalid_request",
            message="Notion leads workspace is not configured. Run setup first.",
            param="data_source_id",
        )

    service = get_notion_leads_service()
    if not service.is_configured():
        raise ApiException(
            status_code=400,
            code="invalid_request",
            message="NOTION_INTEGRATION_SECRET is not configured.",
            param="NOTION_INTEGRATION_SECRET",
        )

    setup = await service.ensure_workspace(
        parent_page_id=parent_page_id,
        database_title=database_title,
        data_source_title=data_source_title,
        database_id=database_id,
        data_source_id=data_source_id,
    )
    await master.update_workflow_key(
        "notion_leads",
        {
            **setup,
            "parent_page_id": parent_page_id or "",
            "updated_at": _now_iso(),
        },
    )
    return {
        "parent_page_id": parent_page_id,
        **setup,
    }


@router.post("/notion/leads/setup")
async def setup_notion_leads(
    body: LeadsSetupRequest,
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
):
    mode = get_mode(request.headers.get("Authorization"))
    livemode = get_livemode(request.headers.get("Authorization"))
    if mode == "demo":
        config = {
            "database_id": "demo_notion_pipeline",
            "data_source_id": "demo_notion_leads",
            "database_title": body.database_title or "Leads",
            "data_source_title": body.data_source_title or "Theo Leads",
            "database_url": "https://www.notion.so/demo_notion_pipeline",
            "schema_version": "crm_leads_v2",
            "parent_page_id": body.parent_page_id or "",
            "updated_at": _now_iso(),
        }
        await master.update_workflow_key("notion_leads", config)
        return {
            "id": generate_id("nlead_setup_"),
            "object": "notion_leads_setup",
            "created": epoch_now(),
            "livemode": livemode,
            "metadata": {},
            **config,
            "reused": True,
        }

    try:
        setup = await _resolve_workspace(master=master, payload=body.model_dump(mode="json"), allow_setup=True)
        return {
            "id": generate_id("nlead_setup_"),
            "object": "notion_leads_setup",
            "created": epoch_now(),
            "livemode": livemode,
            "metadata": {},
            **setup,
        }
    except ApiException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ApiException(status_code=500, code="internal_error", message=str(exc))


@router.post("/notion/leads/sync")
async def sync_notion_leads(
    body: LeadsSyncRequest,
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
):
    mode = get_mode(request.headers.get("Authorization"))
    livemode = get_livemode(request.headers.get("Authorization"))

    if mode == "demo":
        leads = body.leads or default_demo_leads()
        counts = {
            "desired": len(leads),
            "created": 0,
            "updated": 0,
            "noop": len(leads),
            "archived": 0,
        }
        await master.update_workflow_key(
            "notion_leads",
            {
                "database_id": body.database_id or "demo_notion_pipeline",
                "data_source_id": body.data_source_id or "demo_notion_leads",
                "database_title": body.database_title,
                "data_source_title": body.data_source_title,
                "database_url": "https://www.notion.so/demo_notion_pipeline",
                "schema_version": "crm_leads_v2",
                "last_synced_at": _now_iso(),
            },
        )
        return {
            "id": generate_id("nlead_sync_"),
            "object": "notion_leads_sync",
            "created": epoch_now(),
            "livemode": livemode,
            "metadata": {},
            "counts": counts,
            "strict_reconcile": body.strict_reconcile,
            "leads": [normalize_lead_payload(l) for l in leads if isinstance(l, dict)],
        }

    try:
        workspace = await _resolve_workspace(master=master, payload=body.model_dump(mode="json"), allow_setup=True)
        service = get_notion_leads_service()
        sync = await service.sync_leads(
            data_source_id=str(workspace["data_source_id"]),
            leads=[l for l in body.leads if isinstance(l, dict)],
            strict_reconcile=body.strict_reconcile,
        )
        await master.update_workflow_key(
            "notion_leads",
            {
                **workspace,
                "last_synced_at": _now_iso(),
            },
        )
        return {
            "id": generate_id("nlead_sync_"),
            "object": "notion_leads_sync",
            "created": epoch_now(),
            "livemode": livemode,
            "metadata": {},
            **sync,
            "database_id": workspace["database_id"],
            "data_source_id": workspace["data_source_id"],
        }
    except ApiException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ApiException(status_code=500, code="internal_error", message=str(exc))


@router.get("/notion/leads")
async def list_notion_leads(
    request: Request,
    status: str | None = Query(None),
    source: str | None = Query(None),
    lead_type: str | None = Query(None),
    view: Literal["today_followups", "high_value_focus", "warm_inbound", "prospecting"] | None = Query(None),
    min_deal_size: float = Query(1000.0, ge=0.0),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    starting_after: str | None = Query(None),
    master: AlwaysOnMaster = Depends(get_master),
):
    mode = get_mode(request.headers.get("Authorization"))
    livemode = get_livemode(request.headers.get("Authorization"))

    if mode == "demo":
        leads = [normalize_lead_payload(l) for l in default_demo_leads()]
    else:
        try:
            workspace = await _resolve_workspace(master=master, payload={}, allow_setup=False)
            service = get_notion_leads_service()
            leads = await service.list_leads(str(workspace["data_source_id"]))
        except ApiException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ApiException(status_code=500, code="internal_error", message=str(exc))

    if status:
        leads = [l for l in leads if str(l.get("status", "")).lower() == status.lower()]
    if source:
        leads = [l for l in leads if str(l.get("source", "")).lower() == source.lower()]
    if lead_type:
        leads = [l for l in leads if str(l.get("lead_type", "")).lower() == lead_type.lower()]
    if q:
        ql = q.lower()
        leads = [
            l
            for l in leads
            if ql in str(l.get("name", "")).lower()
            or ql in str(l.get("source", "")).lower()
            or ql in str(l.get("notes", "")).lower()
        ]

    leads = _apply_view_filters(leads, view, min_deal_size)
    resources = [
        {
            "id": str(lead.get("lead_key", "")),
            "object": "notion_lead",
            "created": epoch_now(),
            "livemode": livemode,
            "metadata": {},
            **lead,
        }
        for lead in leads
    ]
    page, has_more = paginate(resources, limit=limit, starting_after=starting_after)
    return ListObject(data=page, has_more=has_more, url="/v1/notion/leads").model_dump(mode="json")


@router.patch("/notion/leads/{lead_key}")
async def patch_notion_lead(
    lead_key: str,
    body: LeadsPatchRequest,
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
):
    mode = get_mode(request.headers.get("Authorization"))
    livemode = get_livemode(request.headers.get("Authorization"))

    if mode == "demo":
        return {
            "id": lead_key,
            "object": "notion_lead",
            "created": epoch_now(),
            "livemode": livemode,
            "metadata": {},
            "lead_key": lead_key,
            "patched": True,
        }

    patch = body.model_dump(mode="json")
    patch = {k: v for k, v in patch.items() if v is not None}
    try:
        workspace = await _resolve_workspace(master=master, payload=patch, allow_setup=True)
        service = get_notion_leads_service()
        result = await service.patch_lead(
            data_source_id=str(workspace["data_source_id"]),
            lead_key=lead_key,
            patch=patch,
        )
        return {
            "id": result.get("lead_key", lead_key),
            "object": "notion_lead",
            "created": epoch_now(),
            "livemode": livemode,
            "metadata": {},
            **result.get("lead", {}),
            "page_id": result.get("page_id", ""),
        }
    except ApiException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ApiException(status_code=500, code="internal_error", message=str(exc))


@router.post("/notion/leads/realtime")
async def enqueue_realtime_notion_leads(
    body: LeadsRealtimeRequest,
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
):
    mode = get_mode(request.headers.get("Authorization"))
    livemode = get_livemode(request.headers.get("Authorization"))
    task_payload = dict(body.task_payload or {})
    if mode == "demo":
        task_payload.setdefault("demo_mode", True)

    result = await master.ingest_event(
        "manual_enqueue",
        {
            "enqueue": True,
            "worker_id": "notion_leads_worker",
            "action": body.action,
            "priority": int(body.priority),
            "task_payload": task_payload,
        },
    )
    event = result.get("event", {})
    return {
        "id": event.get("event_id", generate_id("evt_")),
        "object": "event",
        "created": epoch_now(),
        "livemode": livemode,
        "metadata": {},
        "type": event.get("type", "manual_enqueue"),
        "payload": event.get("payload", {}),
        "cycle": result.get("cycle"),
    }

