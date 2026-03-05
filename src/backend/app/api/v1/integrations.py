"""Integration webhooks and service endpoints."""

from __future__ import annotations

import hashlib
import os
from typing import Any

from fastapi import APIRouter, Depends, Header, Request

from app.auth import get_livemode
from app.deps import get_master
from app.middleware.errors import ApiException
from deepagent.loop import AlwaysOnMaster

router = APIRouter()


def _normalize_figma_webhook_payload(payload: dict[str, Any]) -> dict[str, Any]:
    event = payload.get("event", {}) if isinstance(payload.get("event", {}), dict) else {}
    data = payload.get("data", {}) if isinstance(payload.get("data", {}), dict) else {}
    comment = data.get("comment", {}) if isinstance(data.get("comment", {}), dict) else {}
    resource = payload.get("resource", {}) if isinstance(payload.get("resource", {}), dict) else {}

    comment_id = (
        str(payload.get("comment_id", "")).strip()
        or str(comment.get("id", "")).strip()
        or str(event.get("comment_id", "")).strip()
    )
    file_key = (
        str(payload.get("file_key", "")).strip()
        or str(resource.get("file_key", "")).strip()
        or str(comment.get("file_key", "")).strip()
    )
    message = (
        str(payload.get("message", "")).strip()
        or str(comment.get("message", "")).strip()
        or str(event.get("message", "")).strip()
    )
    created_at = (
        str(payload.get("created_at", "")).strip()
        or str(comment.get("created_at", "")).strip()
        or str(event.get("created_at", "")).strip()
    )
    raw_event_id = (
        str(payload.get("event_id", "")).strip()
        or str(payload.get("id", "")).strip()
        or str(event.get("id", "")).strip()
    )
    dedupe_raw = "|".join([raw_event_id, comment_id, file_key, message, created_at])
    dedupe_hash = hashlib.sha256(dedupe_raw.encode()).hexdigest()[:20]

    return {
        "event_id": raw_event_id or f"figma_evt_{dedupe_hash}",
        "comment_id": comment_id,
        "file_key": file_key,
        "message": message,
        "from": payload.get("from") or comment.get("from") or {},
        "created_at": created_at,
        "raw": payload,
    }


@router.post("/integrations/composio/webhook")
async def composio_webhook(
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
    x_composio_webhook_secret: str | None = Header(None),
):
    expected_secret = os.environ.get("COMPOSIO_WEBHOOK_SECRET", "").strip()
    if expected_secret and x_composio_webhook_secret != expected_secret:
        raise ApiException(
            status_code=401,
            code="invalid_request",
            message="Invalid webhook secret.",
            param="x-composio-webhook-secret",
        )

    payload = await request.json()
    normalized = _normalize_figma_webhook_payload(payload if isinstance(payload, dict) else {})
    result = await master.ingest_event("integration.figma.webhook.received", normalized)
    event = result.get("event", {})
    return {
        "id": event.get("event_id", ""),
        "object": "event",
        "type": event.get("type", "integration.figma.webhook.received"),
        "payload": event.get("payload", normalized),
        "livemode": get_livemode(request.headers.get("Authorization")),
        "cycle": result.get("cycle"),
    }
