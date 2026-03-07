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


@pytest.mark.fast
def test_demo_push_ignores_demo_placeholder_workspace_and_resolves_live_workspace(client, monkeypatch):
    import app.api.routes_agent as routes_agent_module
    import app.api.v1.notion_leads as notion_leads_module

    class _FakeService:
        def is_configured(self) -> bool:
            return True

        async def ensure_workspace(  # noqa: ANN001
            self,
            *,
            parent_page_id,
            database_title,
            data_source_title,
            database_id,
            data_source_id,
        ):
            assert database_id is None
            assert data_source_id is None
            return {
                "database_id": "29b3ec6c-4bce-42ca-9e46-28a79466dd53",
                "data_source_id": "5d472424-826f-4719-8ac6-06f0f127e068",
                "database_title": database_title,
                "data_source_title": data_source_title,
                "database_url": "https://www.notion.so/29b3ec6c4bce42ca9e4628a79466dd53",
                "schema_version": "crm_leads_v2",
                "reused": True,
            }

        async def sync_leads(self, *, data_source_id: str, leads: list[dict], strict_reconcile: bool):  # noqa: ANN001
            assert data_source_id == "5d472424-826f-4719-8ac6-06f0f127e068"
            assert strict_reconcile is False
            assert len(leads) == 1
            return {"counts": {"desired": 1, "created": 1, "updated": 0, "noop": 0, "archived": 0}}

    state = client.app.state.always_on_master.store.load()
    state.workflow_state["notion_leads"] = {
        "database_id": "demo_notion_pipeline",
        "data_source_id": "demo_notion_leads",
        "database_title": "Demo Leads",
        "data_source_title": "Demo Leads",
    }
    client.app.state.always_on_master.store.save(state)

    monkeypatch.setattr(routes_agent_module, "get_notion_leads_service", lambda: _FakeService())
    monkeypatch.setattr(notion_leads_module, "get_notion_leads_service", lambda: _FakeService())

    response = client.post("/api/agent/demo/push/04_agency_partnership")

    assert response.status_code == 200
    body = response.json()
    assert body["notion_sync"]["status"] == "completed"
    assert body["notion_sync"]["data_source_id"] == "5d472424-826f-4719-8ac6-06f0f127e068"
