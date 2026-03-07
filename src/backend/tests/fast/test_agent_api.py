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


@pytest.mark.fast
def test_demo_push_syncs_demo_slug_to_live_notion_mapping(client, monkeypatch):
    import app.api.routes_agent as routes_agent_module

    class _FakeService:
        def is_configured(self) -> bool:
            return True

        async def sync_leads(self, *, data_source_id: str, leads: list[dict], strict_reconcile: bool):  # noqa: ANN001
            assert data_source_id == "ds_demo_live"
            assert strict_reconcile is False
            assert len(leads) == 1
            assert leads[0]["lead_key"] == "novabit::direct"
            return {"counts": {"desired": 1, "created": 1, "updated": 0, "noop": 0, "archived": 0}}

    async def _fake_resolve_workspace(master):  # noqa: ANN001
        return {
            "database_id": "db_demo_live",
            "data_source_id": "ds_demo_live",
            "database_title": "Theo Client Pipeline",
            "data_source_title": "Theo Client Pipeline",
            "database_url": "https://www.notion.so/db_demo_live",
            "schema_version": "crm_leads_v2",
        }

    monkeypatch.setattr(routes_agent_module, "get_notion_leads_service", lambda: _FakeService())
    monkeypatch.setattr(routes_agent_module, "_resolve_demo_notion_workspace", _fake_resolve_workspace)

    response = client.post("/api/agent/demo/push/01_high_value_client")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["notion_sync"]["status"] == "completed"
    assert body["notion_sync"]["data_source_id"] == "ds_demo_live"


@pytest.mark.fast
def test_demo_push_skips_notion_sync_when_unconfigured(client, monkeypatch):
    import app.api.routes_agent as routes_agent_module

    class _FakeService:
        def is_configured(self) -> bool:
            return False

    monkeypatch.setattr(routes_agent_module, "get_notion_leads_service", lambda: _FakeService())

    response = client.post("/api/agent/demo/push/03_motion_reel_viral")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["notion_sync"]["status"] == "skipped"
    assert body["notion_sync"]["reason"] == "notion_unconfigured"
