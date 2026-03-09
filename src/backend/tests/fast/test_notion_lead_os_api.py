from __future__ import annotations

import pytest

DEMO_HEADERS = {"Authorization": "Bearer sk_demo_default"}


@pytest.mark.fast
def test_lead_os_tick_and_state_demo(client):
    tick = client.post(
        "/v1/notion/leads/os/tick",
        json={"top_n": 8},
        headers=DEMO_HEADERS,
    )
    assert tick.status_code == 200
    tick_body = tick.json()
    assert tick_body["object"] == "notion_lead_os_tick"
    assert tick_body["leads_reconciled"] >= 1
    assert "pods" in tick_body
    assert "sustainability" in tick_body

    state = client.get(
        "/v1/notion/leads/os/state?top_n=5",
        headers=DEMO_HEADERS,
    )
    assert state.status_code == 200
    state_body = state.json()
    assert state_body["object"] == "notion_lead_os_state"
    assert isinstance(state_body.get("recommended_actions"), list)
    assert "objective" in state_body


@pytest.mark.fast
def test_lead_os_dispatch_dry_run_demo(client):
    tick = client.post(
        "/v1/notion/leads/os/tick",
        json={"top_n": 10},
        headers=DEMO_HEADERS,
    )
    assert tick.status_code == 200

    dispatch = client.post(
        "/v1/notion/leads/os/dispatch",
        json={"limit": 2, "min_score": 0.0, "dry_run": True},
        headers=DEMO_HEADERS,
    )
    assert dispatch.status_code == 200
    body = dispatch.json()
    assert body["object"] == "notion_lead_os_dispatch"
    assert body["dry_run"] is True
    assert body["selected"] <= 2
    assert len(body["dispatches"]) == body["selected"]
    assert body["cycles"] == []
