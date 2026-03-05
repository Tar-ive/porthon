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


@pytest.mark.fast
def test_notion_leads_sync_with_theo_realistic_payload_demo(client):
    payload = {
        "parent_page_id": "Leads-Tracking-25c74e49e5de8035a901cdd614cb3bf7",
        "database_title": "Theo Client Pipeline",
        "data_source_title": "Theo Leads",
        "database_id": "29b3ec6c4bce42ca9e4628a79466dd53",
        "data_source_id": "5d472424-826f-4719-8ac6-06f0f127e068",
        "strict_reconcile": True,
        "leads": [
            {
                "name": "Austin SaaS Founder - Referral",
                "status": "Contacted",
                "lead_type": "Referral",
                "priority": "High",
                "deal_size": 3200,
                "last_contact": "2026-03-05",
                "next_action": "Send scope options and pricing anchors",
                "next_follow_up_date": "2026-03-07",
                "email_handle": "founder@example.com",
                "source": "Referral",
                "notes": "Warm intro from design meetup. Strong fit for brand + motion.",
            },
            {
                "name": "Local Coffee Roaster Website Refresh",
                "status": "Lead",
                "lead_type": "Inbound",
                "priority": "Medium",
                "deal_size": 1800,
                "last_contact": None,
                "next_action": "Send first-touch portfolio samples and discovery call link",
                "next_follow_up_date": "2026-03-08",
                "email_handle": "@localroaster",
                "source": "Portfolio",
                "notes": "Inbound from Instagram portfolio post.",
            },
        ],
    }
    r_sync = client.post("/v1/notion/leads/sync", json=payload, headers=DEMO_HEADERS)
    assert r_sync.status_code == 200
    body = r_sync.json()
    assert body["object"] == "notion_leads_sync"
    assert body["strict_reconcile"] is True
    assert body["counts"]["desired"] == 2
    assert len(body["leads"]) == 2
    assert body["leads"][0]["status"] == "Contacted"
    assert body["leads"][0]["lead_type"] == "Referral"
