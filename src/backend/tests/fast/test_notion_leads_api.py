from __future__ import annotations

import pytest

DEMO_HEADERS = {"Authorization": "Bearer sk_demo_default"}


@pytest.mark.fast
def test_notion_leads_setup_demo(client):
    r = client.post(
        "/v1/notion/leads/setup",
        json={},
        headers=DEMO_HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "notion_leads_setup"
    assert body["database_id"] == "demo_notion_pipeline"
    assert body["data_source_id"] == "demo_notion_leads"


@pytest.mark.fast
def test_notion_leads_sync_and_list_views_demo(client):
    payload = {
        "strict_reconcile": True,
        "leads": [
            {
                "name": "Acme Design",
                "status": "Lead",
                "lead_type": "Inbound",
                "priority": "High",
                "deal_size": 4000,
                "source": "Referral",
                "next_follow_up_date": "2026-03-09",
            },
            {
                "name": "Beta Labs",
                "status": "Won",
                "lead_type": "Outbound",
                "priority": "Low",
                "deal_size": 800,
                "source": "Direct",
            },
        ],
    }
    r_sync = client.post("/v1/notion/leads/sync", json=payload, headers=DEMO_HEADERS)
    assert r_sync.status_code == 200
    assert r_sync.json()["object"] == "notion_leads_sync"

    r_list = client.get("/v1/notion/leads?view=warm_inbound", headers=DEMO_HEADERS)
    assert r_list.status_code == 200
    body = r_list.json()
    assert body["object"] == "list"
    assert isinstance(body["data"], list)


@pytest.mark.fast
def test_notion_leads_patch_and_realtime_demo(client):
    r_patch = client.patch(
        "/v1/notion/leads/referral%20lead::referral",
        json={"status": "Contacted", "next_action": "Send follow-up"},
        headers=DEMO_HEADERS,
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["object"] == "notion_lead"

    r_rt = client.post(
        "/v1/notion/leads/realtime",
        json={
            "action": "upsert_lead",
            "task_payload": {
                "name": "Realtime Lead",
                "source": "Referral",
                "status": "Lead",
            },
        },
        headers=DEMO_HEADERS,
    )
    assert r_rt.status_code == 200
    body = r_rt.json()
    assert body["object"] == "event"
    assert body["type"] == "manual_enqueue"
