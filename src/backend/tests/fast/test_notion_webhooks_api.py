from __future__ import annotations

import hashlib
import hmac
import json

import pytest

DEMO_HEADERS = {"Authorization": "Bearer sk_demo_default"}


def _notion_sig(secret: str, raw_body: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), raw_body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@pytest.mark.fast
def test_notion_webhook_accepts_verification_payload_without_signature(client):
    r = client.post(
        "/v1/notion/webhooks",
        json={
            "type": "url_verification",
            "verification_token": "notion_verify_abc123",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "notion_webhook_event"
    assert body["received"] is True
    assert body["verification_payload"] is True
    assert body["enqueued"] is False


@pytest.mark.fast
def test_notion_webhook_root_and_alias_fallbacks(client):
    payload = {"type": "url_verification", "verification_token": "tok_root_1"}

    r_root = client.post("/", json=payload)
    assert r_root.status_code == 200
    assert r_root.json()["object"] == "notion_webhook_event"

    r_alias = client.post("/notion/webhooks", json=payload)
    assert r_alias.status_code == 200
    assert r_alias.json()["object"] == "notion_webhook_event"


@pytest.mark.fast
def test_notion_webhook_rejects_invalid_signature(client, monkeypatch):
    monkeypatch.setenv("NOTION_WEBHOOK_VERIFICATION_TOKEN", "notion_secret_x")
    payload = {
        "id": "notion_evt_bad_sig",
        "type": "page.properties_updated",
        "entity": {"type": "page", "id": "page_123"},
    }
    raw = json.dumps(payload, separators=(",", ":"))
    r = client.post(
        "/v1/notion/webhooks",
        data=raw,
        headers={
            "Content-Type": "application/json",
            "X-Notion-Signature": "sha256=deadbeef",
        },
    )
    assert r.status_code == 401


@pytest.mark.fast
def test_notion_webhook_signed_event_dedupes(client, monkeypatch):
    monkeypatch.setenv("NOTION_WEBHOOK_VERIFICATION_TOKEN", "notion_secret_x")
    payload = {
        "id": "notion_evt_001",
        "type": "page.properties_updated",
        "workspace_id": "ws_1",
        "integration_id": "int_1",
        "entity": {"type": "page", "id": "page_123"},
    }
    raw = json.dumps(payload, separators=(",", ":"))
    sig = _notion_sig("notion_secret_x", raw)

    first = client.post(
        "/v1/notion/webhooks",
        data=raw,
        headers={"Content-Type": "application/json", "X-Notion-Signature": sig},
    )
    assert first.status_code == 200
    body_first = first.json()
    assert body_first["relevant"] is True
    assert body_first["deduped"] is False
    assert body_first["enqueued"] is True

    second = client.post(
        "/v1/notion/webhooks",
        data=raw,
        headers={"Content-Type": "application/json", "X-Notion-Signature": sig},
    )
    assert second.status_code == 200
    body_second = second.json()
    assert body_second["deduped"] is True
    assert body_second["enqueued"] is False

    runtime = client.get("/v1/runtime", headers=DEMO_HEADERS).json()
    notion_watch = runtime.get("workflow_state", {}).get("notion_watch", {})
    stats = notion_watch.get("stats", {})
    assert int(stats.get("received", 0)) >= 2
    assert int(stats.get("deduped", 0)) >= 1


class _FakeNotionService:
    def is_configured(self) -> bool:
        return True

    async def list_leads(self, data_source_id: str):
        assert data_source_id
        return [
            {
                "name": "Webhook Lead A",
                "status": "Lead",
                "lead_type": "Inbound",
                "priority": "High",
                "deal_size": 2500,
                "source": "Inbound",
                "next_action": "Reply with scoped options",
                "next_follow_up_date": "2026-03-10",
                "lead_key": "webhook lead a::inbound",
            }
        ]


@pytest.mark.fast
def test_integration_notion_event_refreshes_lead_os_state(client, monkeypatch):
    import deepagent.loop as loop_module

    monkeypatch.setattr(loop_module, "get_notion_leads_service", lambda: _FakeNotionService())

    setup = client.post("/v1/notion/leads/setup", json={}, headers=DEMO_HEADERS)
    assert setup.status_code == 200

    evt = client.post(
        "/v1/events",
        json={
            "type": "integration.notion.webhook.received",
            "payload": {
                "event_id": "notion_evt_refresh_1",
                "event_type": "page.properties_updated",
                "entity_type": "page",
                "relevant": True,
            },
        },
        headers=DEMO_HEADERS,
    )
    assert evt.status_code == 200

    runtime = client.get("/v1/runtime", headers=DEMO_HEADERS).json()
    lead_os = runtime.get("workflow_state", {}).get("lead_os", {})
    assert lead_os.get("recommended_actions")
    assert lead_os.get("sustainability", {}).get("open_leads", 0) >= 1

    notion_watch = runtime.get("workflow_state", {}).get("notion_watch", {})
    assert int(notion_watch.get("stats", {}).get("processed", 0)) >= 1
