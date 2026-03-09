"""Integration webhooks and service endpoints."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, Request, Response

from app.auth import get_mode
from app.auth import get_livemode
from app.deps import get_master
from app.middleware.errors import ApiException
from deepagent.loop import AlwaysOnMaster
from integrations.figma_webhooks import normalize_figma_webhook_payload, passcode_matches

router = APIRouter()


@router.post("/integrations/composio/webhook")
async def composio_webhook(
    request: Request,
    response: Response,
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
    normalized = normalize_figma_webhook_payload(payload if isinstance(payload, dict) else {})

    mode = get_mode(request.headers.get("Authorization"))
    expected_passcode = "" if mode == "demo" else os.environ.get("FIGMA_WEBHOOK_PASSCODE", "").strip()
    if not passcode_matches(normalized, expected_passcode):
        raise ApiException(
            status_code=401,
            code="invalid_request",
            message="Invalid Figma webhook passcode.",
            param="passcode",
        )

    response.headers["Deprecation"] = "true"
    response.headers["Link"] = "</v1/figma/webhooks>; rel=\"successor-version\""

    result = await master.ingest_event("integration.figma.webhook.received", normalized)
    event = result.get("event", {})
    return {
        "id": event.get("event_id", ""),
        "object": "event",
        "type": event.get("type", "integration.figma.webhook.received"),
        "payload": event.get("payload", normalized),
        "livemode": get_livemode(request.headers.get("Authorization")),
        "deprecated": True,
        "cycle": result.get("cycle"),
    }
