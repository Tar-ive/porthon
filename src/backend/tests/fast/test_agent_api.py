from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from main import app


@pytest.mark.fast
def test_agent_state_endpoint_shape():
    with TestClient(app) as client:
        response = client.get("/api/agent/state")
        assert response.status_code == 200
        body = response.json()
        assert "workers" in body
        assert "queue" in body


@pytest.mark.fast
def test_agent_map_endpoint_shape():
    with TestClient(app) as client:
        response = client.get("/api/agent/map")
        assert response.status_code == 200
        body = response.json()
        assert "nodes" in body
        assert "edges" in body
        assert any(node["id"] == "master" for node in body["nodes"])


@pytest.mark.fast
def test_agent_skills_endpoint_shape():
    with TestClient(app) as client:
        response = client.get("/api/agent/skills")
        assert response.status_code == 200
        body = response.json()
        assert "skills" in body
        assert any(skill["skill_id"] == "kg-search" for skill in body["skills"])


@pytest.mark.fast
def test_agent_activate_endpoint():
    with TestClient(app) as client:
        response = client.post(
            "/api/agent/activate",
            json={
                "scenario_id": "s_activate",
                "scenario_title": "Activation Scenario",
                "scenario_summary": "summary",
                "scenario_horizon": "5yr",
                "scenario_likelihood": "possible",
                "scenario_tags": ["career"],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body.get("ok") is True
        assert body["active_scenario"]["scenario_id"] == "s_activate"


@pytest.mark.fast
def test_agent_approve_endpoint():
    with TestClient(app) as client:
        client.post(
            "/api/agent/activate",
            json={
                "scenario_id": "s_approve",
                "scenario_title": "Approval Scenario",
                "scenario_summary": "summary",
                "scenario_horizon": "1yr",
                "scenario_likelihood": "possible",
                "scenario_tags": [],
            },
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
        )
        map_res = client.get("/api/agent/map")
        approvals = map_res.json().get("approvals", [])
        assert approvals, "expected at least one pending approval"

        approve_res = client.post(
            "/api/agent/approve",
            json={"approval_id": approvals[0]["approval_id"], "decision": "approved"},
        )
        assert approve_res.status_code == 200
        assert approve_res.json().get("ok") is True
