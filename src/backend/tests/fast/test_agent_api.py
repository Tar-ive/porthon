from __future__ import annotations

import pytest

DEMO_HEADERS = {"Authorization": "Bearer sk_demo_default"}


@pytest.mark.fast
def test_agent_state_endpoint_shape(client):
    response = client.get("/api/agent/state", headers=DEMO_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert "workers" in body
    assert "queue" in body


@pytest.mark.fast
def test_agent_map_endpoint_shape(client):
    response = client.get("/api/agent/map", headers=DEMO_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert "nodes" in body
    assert "edges" in body
    assert any(node["id"] == "master" for node in body["nodes"])


@pytest.mark.fast
def test_agent_skills_endpoint_shape(client):
    response = client.get("/api/agent/skills", headers=DEMO_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert "data" in body or "skills" in body
    skills = body.get("data") or body.get("skills") or []
    assert any(skill["skill_id"] == "kg-search" for skill in skills)


@pytest.mark.fast
def test_agent_activate_endpoint(client):
    response = client.post(
        "/api/agent/activate",
        json={
            "scenario_id": "scen_activate",
            "scenario_title": "Activation Scenario",
            "scenario_summary": "summary",
            "scenario_horizon": "5yr",
            "scenario_likelihood": "possible",
            "scenario_tags": ["career"],
        },
        headers=DEMO_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("ok") is True
    assert body["active_scenario"]["scenario_id"] == "scen_activate"


@pytest.mark.fast
def test_agent_approve_endpoint(client):
    client.post(
        "/api/agent/activate",
        json={
            "scenario_id": "scen_approve",
            "scenario_title": "Approval Scenario",
            "scenario_summary": "summary",
            "scenario_horizon": "1yr",
            "scenario_likelihood": "possible",
            "scenario_tags": [],
        },
        headers=DEMO_HEADERS,
    )
    client.post(
        "/api/agent/events",
        json={
            "type": "manual_enqueue",
            "payload": {
                "enqueue": True,
                "worker_id": "facebook_worker",
                "action": "publish_post",
                "priority": 1,
            },
        },
        headers=DEMO_HEADERS,
    )
    map_res = client.get("/api/agent/map", headers=DEMO_HEADERS)
    approvals = map_res.json().get("approvals", [])
    assert approvals, "expected at least one pending approval"

    approve_res = client.post(
        "/api/agent/approve",
        json={"approval_id": approvals[0]["approval_id"], "decision": "approved"},
        headers=DEMO_HEADERS,
    )
    assert approve_res.status_code == 200
    assert approve_res.json().get("decision") == "approved"
