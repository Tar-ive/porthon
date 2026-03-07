from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

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
                "page_id": "page_webhook_a",
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


@pytest.mark.fast
def test_integration_notion_event_rewrites_mirror_files_and_triggers_watcher(client, monkeypatch, tmp_path):
    import deepagent.loop as loop_module
    import integrations.notion_mirror as notion_mirror_module

    watcher_calls: list[dict[str, object]] = []

    async def _fake_force_check(**kwargs):
        watcher_calls.append(kwargs)

    monkeypatch.setattr(loop_module, "get_notion_leads_service", lambda: _FakeNotionService())
    monkeypatch.setattr(notion_mirror_module, "persona_data_dir", lambda persona_id: tmp_path)
    monkeypatch.setattr(client.app.state.data_watcher, "force_check", _fake_force_check)

    setup = client.post("/v1/notion/leads/setup", json={}, headers=DEMO_HEADERS)
    assert setup.status_code == 200

    evt = client.post(
        "/v1/events",
        json={
            "type": "integration.notion.webhook.received",
            "payload": {
                "event_id": "notion_evt_refresh_files_1",
                "event_type": "page.properties_updated",
                "entity_type": "page",
                "relevant": True,
            },
        },
        headers=DEMO_HEADERS,
    )
    assert evt.status_code == 200

    assert len(watcher_calls) == 1
    watcher_call = watcher_calls[0]
    assert watcher_call["source"] == "live_webhook"
    assert watcher_call["demo_mode"] is False
    assert watcher_call["notion_write"] is True
    assert watcher_call["event_id"] == "notion_evt_refresh_files_1"
    assert watcher_call["changed_domains"] == {
        "notion_leads",
        "time_commitments",
        "budget_commitments",
    }
    changed_paths = {Path(path).name for path in watcher_call["changed_files"]}
    assert changed_paths == {
        "notion_leads.jsonl",
        "time_commitments.jsonl",
        "budget_commitments.jsonl",
    }

    lead_rows = [
        json.loads(line)
        for line in (tmp_path / "notion_leads.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(lead_rows) == 1
    assert lead_rows[0]["lead_key"] == "webhook lead a::inbound"
    assert lead_rows[0]["notion_page_id"] == "page_webhook_a"
    assert lead_rows[0]["external_url"] == "https://www.notion.so/page_webhook_a"
    assert lead_rows[0]["run_id"].startswith("run_")
    assert (tmp_path / "time_commitments.jsonl").read_text() == ""
    assert (tmp_path / "budget_commitments.jsonl").read_text() == ""


@pytest.mark.fast
def test_integration_notion_event_skips_watcher_when_mirror_content_is_unchanged(client, monkeypatch, tmp_path):
    import deepagent.loop as loop_module
    import integrations.notion_mirror as notion_mirror_module

    watcher_calls: list[dict[str, object]] = []

    async def _fake_force_check(**kwargs):
        watcher_calls.append(kwargs)

    monkeypatch.setattr(loop_module, "get_notion_leads_service", lambda: _FakeNotionService())
    monkeypatch.setattr(notion_mirror_module, "persona_data_dir", lambda persona_id: tmp_path)
    monkeypatch.setattr(client.app.state.data_watcher, "force_check", _fake_force_check)

    setup = client.post("/v1/notion/leads/setup", json={}, headers=DEMO_HEADERS)
    assert setup.status_code == 200

    for event_id in ("notion_evt_refresh_same_1", "notion_evt_refresh_same_2"):
        evt = client.post(
            "/v1/events",
            json={
                "type": "integration.notion.webhook.received",
                "payload": {
                    "event_id": event_id,
                    "event_type": "page.properties_updated",
                    "entity_type": "page",
                    "relevant": True,
                },
            },
            headers=DEMO_HEADERS,
        )
        assert evt.status_code == 200

    assert len(watcher_calls) == 1


@pytest.mark.fast
def test_integration_notion_event_ignores_demo_placeholder_workspace_and_uses_env_fallback(
    client,
    monkeypatch,
    tmp_path,
):
    import deepagent.loop as loop_module
    import integrations.notion_mirror as notion_mirror_module

    watcher_calls: list[dict[str, object]] = []

    async def _fake_force_check(**kwargs):
        watcher_calls.append(kwargs)

    monkeypatch.setattr(loop_module, "get_notion_leads_service", lambda: _FakeNotionService())
    monkeypatch.setattr(notion_mirror_module, "persona_data_dir", lambda persona_id: tmp_path)
    monkeypatch.setattr(client.app.state.data_watcher, "force_check", _fake_force_check)
    monkeypatch.setenv("NOTION_LEADS_DATA_SOURCE_ID", "5d472424-826f-4719-8ac6-06f0f127e068")

    state = client.app.state.always_on_master.store.load()
    state.workflow_state["notion_leads"] = {
        "data_source_id": "demo_notion_leads",
        "database_id": "demo_notion_pipeline",
    }
    client.app.state.always_on_master.store.save(state)

    evt = client.post(
        "/v1/events",
        json={
            "type": "integration.notion.webhook.received",
            "payload": {
                "event_id": "notion_evt_refresh_env_fallback_1",
                "event_type": "page.properties_updated",
                "entity_type": "page",
                "relevant": True,
            },
        },
        headers=DEMO_HEADERS,
    )
    assert evt.status_code == 200
    assert len(watcher_calls) == 1

    runtime = client.get("/v1/runtime", headers=DEMO_HEADERS).json()
    repaired = runtime.get("workflow_state", {}).get("notion_leads", {})
    assert repaired.get("data_source_id") == "5d472424-826f-4719-8ac6-06f0f127e068"
