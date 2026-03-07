"""Deterministic Notion leads CRM endpoints."""

from __future__ import annotations

import os
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.api.v1.schemas import ListObject, epoch_now, generate_id, paginate
from app.auth import get_livemode, get_mode
from app.deps import get_master
from app.middleware.errors import ApiException
from deepagent.lead_os import (
    build_pod_snapshot,
    build_recommendations,
    ensure_lead_os_config,
    reconcile_leads,
    sustainability_snapshot,
)
from deepagent.loop import AlwaysOnMaster
from integrations.notion_leads_service import (
    default_demo_leads,
    get_notion_leads_service,
    normalize_lead_payload,
)

router = APIRouter()
logger = logging.getLogger(__name__)


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


class LeadOsTickRequest(BaseModel):
    top_n: int = Field(default=12, ge=1, le=100)


class LeadOsDispatchRequest(BaseModel):
    limit: int = Field(default=5, ge=1, le=20)
    min_score: float = 0.0
    priority: int = Field(default=18, ge=1, le=100)
    dry_run: bool = False


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


_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{32}$|^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _looks_like_uuid(value: str | None) -> bool:
    return bool(_UUID_RE.fullmatch(str(value or "").strip()))


def _configured_workspace_ids(
    *,
    payload: dict[str, Any],
    workflow: dict[str, Any],
) -> tuple[str | None, str | None]:
    database_id = next(
        (
            candidate
            for candidate in (
                str(payload.get("database_id") or "").strip(),
                str(workflow.get("database_id") or "").strip(),
                str(os.environ.get("NOTION_LEADS_DATABASE_ID") or "").strip(),
                str(os.environ.get("NOTION_DATABASE_ID") or "").strip(),
            )
            if _looks_like_uuid(candidate)
        ),
        None,
    )
    data_source_id = next(
        (
            candidate
            for candidate in (
                str(payload.get("data_source_id") or "").strip(),
                str(workflow.get("data_source_id") or "").strip(),
                str(os.environ.get("NOTION_DATA_SOURCE_ID") or "").strip(),
                str(os.environ.get("NOTION_LEADS_DATA_SOURCE_ID") or "").strip(),
            )
            if _looks_like_uuid(candidate)
        ),
        None,
    )
    return database_id, data_source_id


async def _resolve_database_id_for_data_source(
    *,
    service: Any,
    data_source_id: str,
) -> str | None:
    try:
        detail = await service._request("GET", f"/data_sources/{data_source_id}")  # noqa: SLF001
    except Exception:  # noqa: BLE001
        logger.warning("NOTION WORKSPACE DATA SOURCE LOOKUP FAILED data_source_id=%s", data_source_id)
        return None
    database_id = str(service._extract_database_id_from_search_item(detail) or "").strip()  # noqa: SLF001
    return database_id or None


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
    database_id, data_source_id = _configured_workspace_ids(payload=payload, workflow=workflow)

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

    if data_source_id and not database_id:
        database_id = await _resolve_database_id_for_data_source(
            service=service,
            data_source_id=data_source_id,
        )
        if database_id or not allow_setup:
            return {
                "parent_page_id": parent_page_id,
                "database_id": database_id or "",
                "data_source_id": data_source_id,
                "database_title": database_title,
                "data_source_title": data_source_title,
                "database_url": f"https://www.notion.so/{database_id.replace('-', '')}" if database_id else "",
                "schema_version": str(workflow.get("schema_version", "")),
            }

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


async def _load_leads_for_os(master: AlwaysOnMaster, mode: str) -> list[dict[str, Any]]:
    if mode == "demo":
        return [normalize_lead_payload(item) for item in default_demo_leads()]

    try:
        workspace = await _resolve_workspace(master=master, payload={}, allow_setup=False)
    except ApiException:
        return []

    try:
        service = get_notion_leads_service()
        rows = await service.list_leads(str(workspace["data_source_id"]))
        return [normalize_lead_payload(item) for item in rows if isinstance(item, dict)]
    except Exception:  # noqa: BLE001
        return []


def _runtime_queue(state: dict[str, Any]) -> list[dict[str, Any]]:
    raw = state.get("queue", [])
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


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
        await master.update_workflow_key(
            "notion_leads",
            {
                **setup,
                "parent_page_id": body.parent_page_id or setup.get("parent_page_id", "") or "",
                "updated_at": _now_iso(),
            },
        )
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
        logger.info(
            "NOTION API SYNC START mode=%s desired=%s strict_reconcile=%s data_source_id=%s database_title=%s",
            mode,
            len(body.leads),
            body.strict_reconcile,
            body.data_source_id or "",
            body.database_title,
        )
        workspace = await _resolve_workspace(master=master, payload=body.model_dump(mode="json"), allow_setup=True)
        logger.info(
            "NOTION API SYNC WORKSPACE RESOLVED database_id=%s data_source_id=%s",
            workspace.get("database_id", ""),
            workspace.get("data_source_id", ""),
        )
        service = get_notion_leads_service()
        sync = await service.sync_leads(
            data_source_id=str(workspace["data_source_id"]),
            leads=[l for l in body.leads if isinstance(l, dict)],
            strict_reconcile=body.strict_reconcile,
        )
        logger.info(
            "NOTION API SYNC OK database_id=%s data_source_id=%s created=%s updated=%s noop=%s archived=%s",
            workspace.get("database_id", ""),
            workspace.get("data_source_id", ""),
            sync.get("counts", {}).get("created", 0),
            sync.get("counts", {}).get("updated", 0),
            sync.get("counts", {}).get("noop", 0),
            sync.get("counts", {}).get("archived", 0),
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
        logger.exception("NOTION API SYNC FAILED: %s", exc)
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


@router.get("/notion/leads/os/state")
async def get_notion_lead_os_state(
    request: Request,
    top_n: int = Query(12, ge=1, le=100),
    master: AlwaysOnMaster = Depends(get_master),
):
    mode = get_mode(request.headers.get("Authorization"))
    livemode = get_livemode(request.headers.get("Authorization"))
    now_iso = _now_iso()
    runtime_state = await master.get_state()
    persona_id = str(runtime_state.get("persona_id", "p05"))
    queue = _runtime_queue(runtime_state)

    cfg_raw = await master.get_workflow_key("lead_os")
    cfg = ensure_lead_os_config(cfg_raw, persona_id=persona_id, now_iso=now_iso)
    recommendations = build_recommendations(cfg, top_n=top_n)
    pod_snapshot = build_pod_snapshot(cfg, recommendations, queue)
    snapshot = sustainability_snapshot(cfg)

    return {
        "id": generate_id("nlos_"),
        "object": "notion_lead_os_state",
        "created": epoch_now(),
        "livemode": livemode,
        "metadata": {},
        "mode": mode,
        "objective": cfg.get("objective", {}),
        "pods": pod_snapshot,
        "lead_count": len((cfg.get("lead_pcb") or {}).keys()) if isinstance(cfg.get("lead_pcb"), dict) else 0,
        "recommended_actions": recommendations,
        "sustainability": snapshot,
        "updated_at": cfg.get("updated_at", now_iso),
    }


@router.post("/notion/leads/os/tick")
async def tick_notion_lead_os(
    body: LeadOsTickRequest,
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
):
    mode = get_mode(request.headers.get("Authorization"))
    livemode = get_livemode(request.headers.get("Authorization"))
    now_iso = _now_iso()
    runtime_state = await master.get_state()
    persona_id = str(runtime_state.get("persona_id", "p05"))
    queue = _runtime_queue(runtime_state)
    leads = await _load_leads_for_os(master, mode)

    cfg_raw = await master.get_workflow_key("lead_os")
    cfg = ensure_lead_os_config(cfg_raw, persona_id=persona_id, now_iso=now_iso)
    cfg = reconcile_leads(cfg, leads, now_iso=now_iso)
    recommendations = build_recommendations(cfg, top_n=body.top_n)
    cfg["recommended_actions"] = recommendations
    cfg["pods"] = build_pod_snapshot(cfg, recommendations, queue)
    cfg["sustainability"] = sustainability_snapshot(cfg)
    cfg["last_tick_at"] = now_iso
    cfg["updated_at"] = now_iso
    await master.update_workflow_key("lead_os", cfg, merge=False)

    return {
        "id": generate_id("nlos_tick_"),
        "object": "notion_lead_os_tick",
        "created": epoch_now(),
        "livemode": livemode,
        "metadata": {},
        "leads_reconciled": len(leads),
        "recommended_count": len(recommendations),
        "pods": cfg["pods"],
        "sustainability": cfg["sustainability"],
        "updated_at": cfg["updated_at"],
    }


@router.post("/notion/leads/os/dispatch")
async def dispatch_notion_lead_os(
    body: LeadOsDispatchRequest,
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
):
    mode = get_mode(request.headers.get("Authorization"))
    livemode = get_livemode(request.headers.get("Authorization"))
    now_iso = _now_iso()
    runtime_state = await master.get_state()
    persona_id = str(runtime_state.get("persona_id", "p05"))
    leads = await _load_leads_for_os(master, mode)

    cfg_raw = await master.get_workflow_key("lead_os")
    cfg = ensure_lead_os_config(cfg_raw, persona_id=persona_id, now_iso=now_iso)
    cfg = reconcile_leads(cfg, leads, now_iso=now_iso)
    recommendations = build_recommendations(cfg, top_n=max(body.limit * 2, 12))

    selected = [
        item
        for item in recommendations
        if float(item.get("score", 0.0)) >= float(body.min_score)
    ][: body.limit]

    dispatches: list[dict[str, Any]] = []
    cycles: list[dict[str, Any]] = []
    for action in selected:
        task_payload = {
            "lead_key": action.get("lead_key", ""),
            "name": action.get("name", ""),
            "source": action.get("source", "Unknown"),
            "next_action": action.get("next_step", ""),
            "next_follow_up_date": action.get("next_touch_date", datetime.now(UTC).date().isoformat()),
            "priority": action.get("priority", "Medium"),
        }
        if mode == "demo":
            task_payload["demo_mode"] = True

        dispatches.append(
            {
                "lead_key": task_payload["lead_key"],
                "worker_id": "notion_leads_worker",
                "action": "patch_lead",
                "task_payload": task_payload,
            }
        )

        if body.dry_run:
            continue

        result = await master.ingest_event(
            "manual_enqueue",
            {
                "enqueue": True,
                "worker_id": "notion_leads_worker",
                "action": "patch_lead",
                "priority": int(body.priority),
                "task_payload": task_payload,
            },
        )
        cycle = result.get("cycle", {})
        if isinstance(cycle, dict):
            cycles.append(cycle)

    cfg["recommended_actions"] = recommendations
    cfg["pods"] = build_pod_snapshot(cfg, recommendations, _runtime_queue(await master.get_state()))
    cfg["sustainability"] = sustainability_snapshot(cfg)
    cfg["last_dispatch_at"] = now_iso
    cfg["dispatch_log"] = (
        [entry for entry in cfg.get("dispatch_log", []) if isinstance(entry, dict)]
        + [
            {
                "dispatched_at": now_iso,
                "count": len(dispatches),
                "dry_run": body.dry_run,
                "lead_keys": [str(item.get("lead_key", "")) for item in selected],
            }
        ]
    )[-50:]
    cfg["updated_at"] = now_iso
    await master.update_workflow_key("lead_os", cfg, merge=False)

    return {
        "id": generate_id("nlos_dispatch_"),
        "object": "notion_lead_os_dispatch",
        "created": epoch_now(),
        "livemode": livemode,
        "metadata": {},
        "dry_run": body.dry_run,
        "requested": body.limit,
        "selected": len(selected),
        "dispatches": dispatches,
        "cycles": cycles,
        "sustainability": cfg["sustainability"],
        "updated_at": cfg["updated_at"],
    }


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
