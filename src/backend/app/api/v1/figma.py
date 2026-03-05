"""Direct Figma webhook/watcher endpoints."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.api.v1.schemas import ListObject, epoch_now, generate_id, paginate
from app.auth import get_livemode, get_mode
from app.deps import get_master
from app.middleware.errors import ApiException
from deepagent.lead_os import ensure_lead_os_config, figma_actor_file_key
from deepagent.loop import AlwaysOnMaster
from integrations.figma_api import FigmaApiError, get_figma_api
from integrations.figma_webhooks import normalize_figma_webhook_payload, passcode_matches
from integrations.notion_leads_service import canonical_lead_key

router = APIRouter()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _watcher_resource(watcher: dict[str, Any], livemode: bool) -> dict[str, Any]:
    return {
        "id": str(watcher.get("watcher_id", "")),
        "object": "figma_watcher",
        "created": epoch_now(),
        "livemode": livemode,
        "metadata": {},
        "webhook_id": str(watcher.get("webhook_id", "")),
        "event_type": str(watcher.get("event_type", "FILE_COMMENT")),
        "endpoint": str(watcher.get("endpoint", "")),
        "context": str(watcher.get("context", "file")),
        "context_id": str(watcher.get("context_id", "")),
        "file_key": str(watcher.get("file_key", "")),
        "status": str(watcher.get("status", "ACTIVE")),
        "enabled": bool(watcher.get("enabled", True)),
        "description": str(watcher.get("description", "")),
        "created_at": str(watcher.get("created_at", "")),
        "updated_at": str(watcher.get("updated_at", "")),
    }


def _load_watchers(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    raw = cfg.get("watchers", [])
    if not isinstance(raw, list):
        return []
    return [w for w in raw if isinstance(w, dict)]


def _save_watchers_patch(watchers: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "watchers": watchers,
        "updated_at": _now_iso(),
    }


def _resolve_comment_send_status(item: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    out = dict(item)
    queue = state.get("queue", [])
    approvals = state.get("approvals", [])
    comment_id = str(out.get("comment_id", ""))
    tasks = [
        t
        for t in queue
        if t.get("worker_id") == "figma_worker"
        and t.get("action") == "reply_comment"
        and str((t.get("payload") or {}).get("comment_id", "")) == comment_id
    ]
    if not tasks:
        return out

    tasks.sort(key=lambda t: str(t.get("updated_at", "")))
    latest = tasks[-1]
    task_status = str(latest.get("status", ""))
    out["send_task_id"] = latest.get("task_id")

    if task_status == "waiting_approval":
        out["status"] = "awaiting_approval"
        pending_approval = next(
            (
                a
                for a in approvals
                if a.get("task_id") == latest.get("task_id") and a.get("decision") is None
            ),
            None,
        )
        if pending_approval:
            out["approval_id"] = pending_approval.get("approval_id")
    elif task_status == "completed":
        out["status"] = "sent"
    elif task_status == "failed":
        out["status"] = "failed"
    elif task_status in {"pending", "running"}:
        out["status"] = "sending"

    return out


class CreateFigmaWatcherRequest(BaseModel):
    file_key: str = Field(..., min_length=1)
    endpoint: str = Field(..., min_length=1)
    event_type: str = "FILE_COMMENT"
    passcode: str | None = None
    description: str | None = None
    context: Literal["file", "team", "project"] = "file"
    context_id: str | None = None
    status: Literal["ACTIVE", "PAUSED"] = "ACTIVE"


class UpdateFigmaWatcherRequest(BaseModel):
    endpoint: str | None = None
    passcode: str | None = None
    description: str | None = None
    status: Literal["ACTIVE", "PAUSED"] | None = None
    enabled: bool | None = None


class PrepareSendReplyRequest(BaseModel):
    message: str | None = None
    priority: int = Field(default=12, ge=1, le=100)


class PromoteFigmaCommentRequest(BaseModel):
    lead_name: str | None = None
    priority: Literal["High", "Medium", "Low"] = "Medium"
    deal_size: float = Field(default=1500.0, ge=0.0)
    next_action: str | None = None
    next_follow_up_date: str | None = None
    dispatch_now: bool = True


@router.post("/figma/watchers")
async def create_figma_watcher(
    body: CreateFigmaWatcherRequest,
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
):
    mode = get_mode(request.headers.get("Authorization"))
    livemode = get_livemode(request.headers.get("Authorization"))
    cfg = await master.get_workflow_key("figma_watch")
    watchers = _load_watchers(cfg)
    now = _now_iso()

    existing = next(
        (
            w
            for w in watchers
            if str(w.get("file_key", "")) == body.file_key
            and str(w.get("endpoint", "")) == body.endpoint
            and str(w.get("event_type", "FILE_COMMENT")) == body.event_type
        ),
        None,
    )
    if existing:
        existing["updated_at"] = now
        await master.update_workflow_key(
            "figma_watch",
            {
                **_save_watchers_patch(watchers),
                "enabled": True,
                "file_key": body.file_key,
                "demo_mode": mode == "demo",
            },
        )
        return {
            **_watcher_resource(existing, livemode),
            "reused": True,
        }

    passcode = (
        (body.passcode or "").strip()
        or os.environ.get("FIGMA_WEBHOOK_PASSCODE", "").strip()
        or f"figma_pass_{generate_id('')[:12]}"
    )
    watcher_id = generate_id("fgw_")
    context_id = (body.context_id or body.file_key).strip()
    webhook_id = f"demo_wh_{watcher_id[-10:]}"

    if mode != "demo":
        api = get_figma_api()
        if not api.is_configured():
            raise ApiException(
                status_code=400,
                code="invalid_request",
                message="FIGMA_API_KEY is not configured.",
                param="FIGMA_API_KEY",
            )
        try:
            created = await api.create_webhook(
                event_type=body.event_type,
                endpoint=body.endpoint,
                passcode=passcode,
                context=body.context,
                context_id=context_id,
                status=body.status,
                description=body.description,
            )
        except FigmaApiError as exc:
            raise ApiException(
                status_code=502,
                code="upstream_error",
                message=f"Figma webhook create failed ({exc.status_code}).",
            )
        webhook = created.get("webhook", created)
        webhook_id = str(webhook.get("id", webhook_id))

    watcher = {
        "watcher_id": watcher_id,
        "webhook_id": webhook_id,
        "event_type": body.event_type,
        "endpoint": body.endpoint,
        "passcode": passcode,
        "context": body.context,
        "context_id": context_id,
        "file_key": body.file_key,
        "status": body.status,
        "enabled": body.status != "PAUSED",
        "description": body.description or "",
        "created_at": now,
        "updated_at": now,
    }
    watchers.append(watcher)
    await master.update_workflow_key(
        "figma_watch",
        {
            **_save_watchers_patch(watchers),
            "enabled": True,
            "file_key": body.file_key,
            "demo_mode": mode == "demo",
            "seen_event_ids": cfg.get("seen_event_ids", []),
        },
    )
    return _watcher_resource(watcher, livemode)


@router.get("/figma/watchers")
async def list_figma_watchers(
    request: Request,
    enabled: bool | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    starting_after: str | None = Query(None),
    master: AlwaysOnMaster = Depends(get_master),
):
    livemode = get_livemode(request.headers.get("Authorization"))
    cfg = await master.get_workflow_key("figma_watch")
    watchers = _load_watchers(cfg)
    if enabled is not None:
        watchers = [w for w in watchers if bool(w.get("enabled", True)) is enabled]
    resources = [_watcher_resource(w, livemode) for w in watchers]
    page, has_more = paginate(resources, limit=limit, starting_after=starting_after)
    return ListObject(data=page, has_more=has_more, url="/v1/figma/watchers").model_dump(mode="json")


@router.patch("/figma/watchers/{watcher_id}")
async def patch_figma_watcher(
    watcher_id: str,
    body: UpdateFigmaWatcherRequest,
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
):
    mode = get_mode(request.headers.get("Authorization"))
    livemode = get_livemode(request.headers.get("Authorization"))
    cfg = await master.get_workflow_key("figma_watch")
    watchers = _load_watchers(cfg)
    idx = next((i for i, w in enumerate(watchers) if str(w.get("watcher_id", "")) == watcher_id), -1)
    if idx < 0:
        raise ApiException(status_code=404, code="resource_missing", message="Figma watcher not found.", param="watcher_id")

    watcher = dict(watchers[idx])
    updates = body.model_dump(mode="json", exclude_none=True)

    if "enabled" in updates and "status" not in updates:
        updates["status"] = "ACTIVE" if updates["enabled"] else "PAUSED"
    if "status" in updates and "enabled" not in updates:
        updates["enabled"] = updates["status"] != "PAUSED"

    if mode != "demo" and watcher.get("webhook_id"):
        figma_updates: dict[str, Any] = {}
        for key in ("endpoint", "passcode", "description", "status"):
            if key in updates:
                figma_updates[key] = updates[key]
        if figma_updates:
            api = get_figma_api()
            if not api.is_configured():
                raise ApiException(status_code=400, code="invalid_request", message="FIGMA_API_KEY is not configured.", param="FIGMA_API_KEY")
            try:
                await api.update_webhook(str(watcher.get("webhook_id")), **figma_updates)
            except FigmaApiError as exc:
                raise ApiException(status_code=502, code="upstream_error", message=f"Figma webhook update failed ({exc.status_code}).")

    watcher.update(updates)
    watcher["updated_at"] = _now_iso()
    watchers[idx] = watcher
    await master.update_workflow_key("figma_watch", _save_watchers_patch(watchers))
    return _watcher_resource(watcher, livemode)


@router.delete("/figma/watchers/{watcher_id}")
async def delete_figma_watcher(
    watcher_id: str,
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
):
    mode = get_mode(request.headers.get("Authorization"))
    cfg = await master.get_workflow_key("figma_watch")
    watchers = _load_watchers(cfg)
    watcher = next((w for w in watchers if str(w.get("watcher_id", "")) == watcher_id), None)
    if watcher is None:
        raise ApiException(status_code=404, code="resource_missing", message="Figma watcher not found.", param="watcher_id")

    if mode != "demo" and watcher.get("webhook_id"):
        api = get_figma_api()
        if api.is_configured():
            try:
                await api.delete_webhook(str(watcher.get("webhook_id")))
            except FigmaApiError:
                pass

    remaining = [w for w in watchers if str(w.get("watcher_id", "")) != watcher_id]
    await master.update_workflow_key("figma_watch", _save_watchers_patch(remaining))
    return {"id": watcher_id, "object": "figma_watcher", "deleted": True}


@router.get("/figma/watchers/{watcher_id}/requests")
async def get_figma_watcher_requests(
    watcher_id: str,
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
):
    mode = get_mode(request.headers.get("Authorization"))
    livemode = get_livemode(request.headers.get("Authorization"))
    cfg = await master.get_workflow_key("figma_watch")
    watchers = _load_watchers(cfg)
    watcher = next((w for w in watchers if str(w.get("watcher_id", "")) == watcher_id), None)
    if watcher is None:
        raise ApiException(status_code=404, code="resource_missing", message="Figma watcher not found.", param="watcher_id")

    if mode == "demo":
        return ListObject(
            data=[
                {
                    "id": generate_id("fwhreq_"),
                    "object": "figma_webhook_request",
                    "created": epoch_now(),
                    "livemode": livemode,
                    "metadata": {},
                    "webhook_id": watcher.get("webhook_id", ""),
                    "status": "200",
                    "received_at": watcher.get("updated_at", _now_iso()),
                }
            ],
            has_more=False,
            url=f"/v1/figma/watchers/{watcher_id}/requests",
        ).model_dump(mode="json")

    api = get_figma_api()
    if not api.is_configured():
        raise ApiException(status_code=400, code="invalid_request", message="FIGMA_API_KEY is not configured.", param="FIGMA_API_KEY")
    try:
        payload = await api.get_webhook_requests(str(watcher.get("webhook_id", "")))
    except FigmaApiError as exc:
        raise ApiException(status_code=502, code="upstream_error", message=f"Figma webhook request fetch failed ({exc.status_code}).")

    requests = payload.get("requests", payload if isinstance(payload, list) else [])
    if not isinstance(requests, list):
        requests = []
    resources = [
        {
            "id": str(r.get("id", generate_id("fwhreq_"))),
            "object": "figma_webhook_request",
            "created": epoch_now(),
            "livemode": livemode,
            "metadata": {},
            **r,
        }
        for r in requests
        if isinstance(r, dict)
    ]
    return ListObject(
        data=resources,
        has_more=False,
        url=f"/v1/figma/watchers/{watcher_id}/requests",
    ).model_dump(mode="json")


@router.post("/figma/webhooks")
async def receive_figma_webhook(
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
):
    payload = await request.json()
    normalized = normalize_figma_webhook_payload(payload if isinstance(payload, dict) else {})
    cfg = await master.get_workflow_key("figma_watch")
    watchers = _load_watchers(cfg)
    webhook_id = str(normalized.get("webhook_id", "")).strip()
    watcher = next((w for w in watchers if str(w.get("webhook_id", "")) == webhook_id), None)

    expected_passcode = (
        str((watcher or {}).get("passcode", "")).strip()
        or os.environ.get("FIGMA_WEBHOOK_PASSCODE", "").strip()
    )
    if not passcode_matches(normalized, expected_passcode):
        raise ApiException(
            status_code=401,
            code="invalid_request",
            message="Invalid Figma webhook passcode.",
            param="passcode",
        )

    if watcher and watcher.get("enabled") is False:
        return {
            "id": normalized.get("event_id", ""),
            "object": "event",
            "type": "integration.figma.webhook.ignored",
            "payload": normalized,
            "livemode": get_livemode(request.headers.get("Authorization")),
            "ignored": True,
        }

    if watcher and not normalized.get("file_key"):
        normalized["file_key"] = str(watcher.get("file_key", ""))
    if watcher:
        normalized["watcher_id"] = str(watcher.get("watcher_id", ""))

    mode = get_mode(request.headers.get("Authorization"))
    normalized.setdefault("demo_mode", mode == "demo")

    result = await master.ingest_event("integration.figma.webhook.received", normalized)
    event = result.get("event", {})
    return {
        "id": event.get("event_id", ""),
        "object": "event",
        "created": epoch_now(),
        "livemode": get_livemode(request.headers.get("Authorization")),
        "metadata": {},
        "type": event.get("type", "integration.figma.webhook.received"),
        "payload": event.get("payload", normalized),
        "cycle": result.get("cycle"),
    }


@router.get("/figma/comments/pending")
async def list_pending_figma_comments(
    request: Request,
    status: Literal["ready_to_send", "awaiting_approval", "sending", "sent", "failed"] | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    starting_after: str | None = Query(None),
    master: AlwaysOnMaster = Depends(get_master),
):
    state = await master.get_state()
    livemode = get_livemode(request.headers.get("Authorization"))
    pending = (
        state.get("demo_artifacts", {})
        .get("figma_watch", {})
        .get("pending_items", [])
    )
    if not isinstance(pending, list):
        pending = []
    resources: list[dict[str, Any]] = []
    for item in pending:
        if not isinstance(item, dict):
            continue
        resolved = _resolve_comment_send_status(item, state)
        if status and str(resolved.get("status", "")) != status:
            continue
        resources.append(
            {
                "id": str(resolved.get("comment_id", generate_id("figc_"))),
                "object": "figma_pending_comment",
                "created": epoch_now(),
                "livemode": livemode,
                "metadata": {},
                **resolved,
            }
        )

    page, has_more = paginate(resources, limit=limit, starting_after=starting_after)
    return ListObject(data=page, has_more=has_more, url="/v1/figma/comments/pending").model_dump(mode="json")


@router.post("/figma/comments/{comment_id}/prepare-send")
async def prepare_send_figma_comment(
    comment_id: str,
    body: PrepareSendReplyRequest,
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
):
    state = await master.get_state()
    pending = (
        state.get("demo_artifacts", {})
        .get("figma_watch", {})
        .get("pending_items", [])
    )
    if not isinstance(pending, list):
        pending = []

    item = next((p for p in pending if isinstance(p, dict) and str(p.get("comment_id", "")) == comment_id), None)
    if item is None:
        raise ApiException(status_code=404, code="resource_missing", message="Pending Figma comment not found.", param="comment_id")

    file_key = str(item.get("file_key", "")).strip()
    message = str(body.message or item.get("draft_reply", "")).strip()
    if not file_key or not message:
        raise ApiException(
            status_code=400,
            code="invalid_request",
            message="Cannot prepare send without file_key and message.",
            param="message",
        )

    mode = get_mode(request.headers.get("Authorization"))
    enqueue_payload = {
        "enqueue": True,
        "worker_id": "figma_worker",
        "action": "reply_comment",
        "priority": body.priority,
        "task_payload": {
            "file_key": file_key,
            "comment_id": comment_id,
            "message": message,
            "demo_mode": mode == "demo",
        },
    }
    cycle_result = await master.ingest_event("manual_enqueue", enqueue_payload)
    latest_state = await master.get_state()
    resolved_item = _resolve_comment_send_status(item, latest_state)
    return {
        "id": str(comment_id),
        "object": "figma_comment_send_request",
        "created": epoch_now(),
        "livemode": get_livemode(request.headers.get("Authorization")),
        "metadata": {},
        "comment_id": comment_id,
        "file_key": file_key,
        "message": message,
        "status": resolved_item.get("status", "awaiting_approval"),
        "approval_id": resolved_item.get("approval_id"),
        "send_task_id": resolved_item.get("send_task_id"),
        "cycle": cycle_result.get("cycle"),
    }


@router.post("/figma/comments/{comment_id}/promote-to-lead")
async def promote_figma_comment_to_lead(
    comment_id: str,
    body: PromoteFigmaCommentRequest,
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
):
    state = await master.get_state()
    livemode = get_livemode(request.headers.get("Authorization"))
    mode = get_mode(request.headers.get("Authorization"))
    pending = (
        state.get("demo_artifacts", {})
        .get("figma_watch", {})
        .get("pending_items", [])
    )
    if not isinstance(pending, list):
        pending = []

    item = next((p for p in pending if isinstance(p, dict) and str(p.get("comment_id", "")) == comment_id), None)
    if item is None:
        raise ApiException(status_code=404, code="resource_missing", message="Pending Figma comment not found.", param="comment_id")

    actor = item.get("from", {}) if isinstance(item.get("from", {}), dict) else {}
    actor_handle = str(actor.get("handle") or actor.get("id") or "figma-collaborator").strip()
    file_key = str(item.get("file_key", "")).strip()
    source = "Inbound"
    lead_name = str(body.lead_name or f"{actor_handle} (Figma)").strip() or "Figma Lead"

    now = datetime.now(UTC).date()
    next_follow_up_date = (
        str(body.next_follow_up_date or "").strip()
        or (now + timedelta(days=2)).isoformat()
    )
    next_action = (
        str(body.next_action or "").strip()
        or "Reply in Figma and propose one concrete next design step"
    )

    lead_os_cfg = ensure_lead_os_config(
        await master.get_workflow_key("lead_os"),
        persona_id=str(state.get("persona_id", "p05")),
        now_iso=_now_iso(),
    )
    comment_links = lead_os_cfg.get("figma_comment_links", {})
    if not isinstance(comment_links, dict):
        comment_links = {}
    actor_links = lead_os_cfg.get("figma_actor_file_links", {})
    if not isinstance(actor_links, dict):
        actor_links = {}

    actor_key = figma_actor_file_key(file_key=file_key, actor_handle=actor_handle)
    existing_lead_key = str(comment_links.get(comment_id) or actor_links.get(actor_key) or "").strip()
    lead_key = existing_lead_key or canonical_lead_key(lead_name, source)

    notes = (
        f"Promoted from Figma comment {comment_id} in file {file_key}. "
        f"Actor: {actor_handle}. Message: {str(item.get('message', '')).strip()}"
    )
    task_payload = {
        "lead_key": lead_key,
        "name": lead_name,
        "status": "Contacted",
        "lead_type": "Inbound",
        "priority": body.priority,
        "deal_size": body.deal_size,
        "source": source,
        "next_action": next_action,
        "next_follow_up_date": next_follow_up_date,
        "notes": notes,
    }
    if mode == "demo":
        task_payload["demo_mode"] = True

    upsert_result = await master.ingest_event(
        "manual_enqueue",
        {
            "enqueue": True,
            "worker_id": "notion_leads_worker",
            "action": "upsert_lead",
            "priority": 16,
            "task_payload": task_payload,
        },
    )

    dispatch_cycle: dict[str, Any] | None = None
    if body.dispatch_now:
        dispatch_result = await master.ingest_event(
            "manual_enqueue",
            {
                "enqueue": True,
                "worker_id": "notion_leads_worker",
                "action": "patch_lead",
                "priority": 18,
                "task_payload": {
                    "lead_key": lead_key,
                    "next_action": next_action,
                    "next_follow_up_date": next_follow_up_date,
                    "source": source,
                    "demo_mode": mode == "demo",
                },
            },
        )
        raw_cycle = dispatch_result.get("cycle", {})
        dispatch_cycle = raw_cycle if isinstance(raw_cycle, dict) else None

    comment_links[comment_id] = lead_key
    actor_links[actor_key] = lead_key
    lead_os_cfg["figma_comment_links"] = comment_links
    lead_os_cfg["figma_actor_file_links"] = actor_links
    lead_os_cfg["last_promoted_comment"] = {
        "comment_id": comment_id,
        "lead_key": lead_key,
        "promoted_at": _now_iso(),
    }
    await master.update_workflow_key("lead_os", lead_os_cfg, merge=False)

    upsert_cycle = upsert_result.get("cycle", {})
    return {
        "id": str(comment_id),
        "object": "figma_comment_lead_promotion",
        "created": epoch_now(),
        "livemode": livemode,
        "metadata": {},
        "comment_id": comment_id,
        "file_key": file_key,
        "actor_handle": actor_handle,
        "lead_key": lead_key,
        "lead_name": lead_name,
        "source": source,
        "next_action": next_action,
        "next_follow_up_date": next_follow_up_date,
        "upsert_cycle": upsert_cycle if isinstance(upsert_cycle, dict) else None,
        "dispatch_cycle": dispatch_cycle,
    }
