"""Notion webhook ingestion for lead automation."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.v1.schemas import epoch_now, generate_id
from app.deps import get_master
from app.middleware.errors import ApiException
from deepagent.loop import AlwaysOnMaster

router = APIRouter()
logger = logging.getLogger(__name__)
NOTION_WEBHOOK_EVENT_RETENTION_DAYS = 7
NOTION_WEBHOOK_MAX_SEEN_EVENTS = 2000


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_iso(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _token_candidates(payload: dict[str, Any], request: Request) -> list[str]:
    values = [
        payload.get("verification_token"),
        payload.get("token"),
        payload.get("challenge"),
        request.headers.get("Notion-Verification-Token"),
        request.headers.get("X-Notion-Verification-Token"),
        request.query_params.get("verification_token"),
        request.query_params.get("token"),
        request.query_params.get("challenge"),
    ]
    out: list[str] = []
    for item in values:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _is_verification_payload(payload: dict[str, Any], request: Request) -> bool:
    event_type = str(payload.get("type") or payload.get("event_type") or "").strip().lower()
    if event_type in {"url_verification", "verification"}:
        return True
    return bool(_token_candidates(payload, request))


def _extract_signature(request: Request) -> str:
    header = str(request.headers.get("X-Notion-Signature", "")).strip()
    if not header:
        return ""
    if header.lower().startswith("sha256="):
        return header.split("=", 1)[1].strip().lower()
    return header.lower()


def _verify_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _is_lead_relevant_event(event_type: str, entity_type: str) -> bool:
    t = str(event_type or "").strip().lower()
    e = str(entity_type or "").strip().lower()
    if t.startswith("page.") or t.startswith("data_source.") or t.startswith("database."):
        return True
    return e in {"page", "data_source", "database"}


def _normalize_event(payload: dict[str, Any], body_digest: str) -> dict[str, Any]:
    event_type = str(payload.get("type") or payload.get("event_type") or "unknown").strip()
    entity = payload.get("entity", {})
    if not isinstance(entity, dict):
        entity = {}
    entity_type = str(entity.get("type") or payload.get("entity_type") or "").strip()
    entity_id = str(entity.get("id") or payload.get("entity_id") or "").strip()
    event_id = str(payload.get("id") or payload.get("event_id") or "").strip()
    if not event_id:
        event_id = f"notion_body_{body_digest[:20]}"

    attempt_raw = payload.get("attempt_number", 1)
    try:
        attempt_number = int(attempt_raw)
    except (TypeError, ValueError):
        attempt_number = 1

    normalized = {
        "event_id": event_id,
        "id": event_id,
        "event_type": event_type,
        "workspace_id": str(payload.get("workspace_id", "")).strip(),
        "integration_id": str(payload.get("integration_id", "")).strip(),
        "attempt_number": attempt_number,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "timestamp": str(payload.get("timestamp") or payload.get("created_at") or "").strip(),
    }
    normalized["relevant"] = _is_lead_relevant_event(event_type, entity_type)
    return normalized


def _compact_seen_events(entries: Any, now: datetime) -> list[dict[str, str]]:
    if not isinstance(entries, list):
        return []
    cutoff = now - timedelta(days=NOTION_WEBHOOK_EVENT_RETENTION_DAYS)
    compact: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for item in entries:
        if not isinstance(item, dict):
            continue
        event_id = str(item.get("id", "")).strip()
        seen_at = _parse_iso(item.get("seen_at"))
        if not event_id or seen_at is None or seen_at < cutoff:
            continue
        if event_id in seen_ids:
            continue
        compact.append({"id": event_id, "seen_at": seen_at.isoformat()})
        seen_ids.add(event_id)
    compact.sort(key=lambda x: x["seen_at"])
    return compact[-NOTION_WEBHOOK_MAX_SEEN_EVENTS :]


async def _ingest_async(master: AlwaysOnMaster, payload: dict[str, Any]) -> None:
    try:
        await master.ingest_event("integration.notion.webhook.received", payload)
    except Exception:  # noqa: BLE001
        logger.exception("Notion webhook async ingest failed")


@router.post("/notion/webhooks")
async def notion_webhooks_verify(
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
):
    raw_body = await request.body()
    try:
        payload_any = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception as exc:  # noqa: BLE001
        raise ApiException(
            status_code=400,
            code="invalid_request",
            message="Invalid JSON payload.",
            param="body",
        ) from exc

    if not isinstance(payload_any, dict):
        raise ApiException(
            status_code=400,
            code="invalid_request",
            message="JSON object payload required.",
            param="body",
        )
    payload = payload_any

    verification_payload = _is_verification_payload(payload, request)
    verification_tokens = _token_candidates(payload, request)
    signature = _extract_signature(request)
    secret = os.environ.get("NOTION_WEBHOOK_VERIFICATION_TOKEN", "").strip()

    if not verification_payload:
        if not secret:
            raise ApiException(
                status_code=500,
                code="internal_error",
                message="NOTION_WEBHOOK_VERIFICATION_TOKEN not configured",
                param="NOTION_WEBHOOK_VERIFICATION_TOKEN",
            )
        if not signature or not _verify_signature(raw_body, signature, secret):
            cfg = await master.get_workflow_key("notion_watch")
            stats = cfg.get("stats", {})
            if not isinstance(stats, dict):
                stats = {}
            stats["invalid_signature"] = int(stats.get("invalid_signature", 0)) + 1
            cfg["stats"] = stats
            cfg["updated_at"] = _now_iso()
            await master.update_workflow_key("notion_watch", cfg, merge=False)
            raise ApiException(
                status_code=401,
                code="invalid_request",
                message="Invalid Notion webhook signature.",
                param="X-Notion-Signature",
            )

    body_digest = hashlib.sha256(raw_body).hexdigest()
    normalized = _normalize_event(payload, body_digest)
    event_id = str(normalized.get("event_id", "")).strip()
    event_type = str(normalized.get("event_type", "")).strip()
    relevant = bool(normalized.get("relevant", False))

    now = datetime.now(UTC)
    cfg = await master.get_workflow_key("notion_watch")
    seen = _compact_seen_events(cfg.get("seen_events", []), now)
    seen_ids = {str(item.get("id", "")) for item in seen}

    deduped = bool(event_id and event_id in seen_ids)
    enqueued = False
    if event_id and not deduped:
        seen.append({"id": event_id, "seen_at": now.isoformat()})
        seen = _compact_seen_events(seen, now)

    stats = cfg.get("stats", {})
    if not isinstance(stats, dict):
        stats = {}
    stats["received"] = int(stats.get("received", 0)) + 1
    if deduped:
        stats["deduped"] = int(stats.get("deduped", 0)) + 1
    if not relevant:
        stats["ignored"] = int(stats.get("ignored", 0)) + 1
    if relevant and not deduped:
        stats["accepted"] = int(stats.get("accepted", 0)) + 1
        enqueued = True

    cfg.update(
        {
            "seen_events": seen,
            "stats": stats,
            "last_event_id": event_id,
            "last_event_type": event_type,
            "last_event_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "event_retention_days": NOTION_WEBHOOK_EVENT_RETENTION_DAYS,
        }
    )
    await master.update_workflow_key("notion_watch", cfg, merge=False)

    logger.info(
        "NOTION WEBHOOK RECEIVED event_id=%s type=%s relevant=%s deduped=%s entity=%s:%s",
        event_id,
        event_type,
        relevant,
        deduped,
        normalized.get("entity_type", ""),
        normalized.get("entity_id", ""),
    )
    if verification_payload and verification_tokens:
        logger.info(
            "NOTION WEBHOOK VERIFICATION TOKEN token=%s",
            verification_tokens[0],
        )

    if enqueued:
        asyncio.create_task(_ingest_async(master, normalized))

    return {
        "id": generate_id("nwh_"),
        "object": "notion_webhook_event",
        "created": epoch_now(),
        "received": True,
        "event_id": event_id,
        "event_type": event_type,
        "relevant": relevant,
        "deduped": deduped,
        "enqueued": enqueued,
        "verification_payload": verification_payload,
        "verification_token": verification_tokens[0] if verification_tokens else "",
    }
