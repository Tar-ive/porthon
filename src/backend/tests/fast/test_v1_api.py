"""Tests for /v1/ API endpoints — covers bugs found during integration and backward compat."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Set env BEFORE importing app to skip KG initialization
os.environ["NEO4J_URI"] = ""  # Disable KG
os.environ["LLM_BINDING_API_KEY"] = "test"  # Mock LLM

# Also clear the rag_storage path to skip KV store loading
os.environ["RAG_STORAGE_DIR"] = ""

from fastapi.testclient import TestClient
import pytest

from main import app


# ---------------------------------------------------------------------------
# Mock LLM calls for tests
# ---------------------------------------------------------------------------

# Mock scenario generation
MOCK_SCENARIOS = [
    {
        "id": "s_test_v1",
        "title": "Test",
        "summary": "Test scenario",
        "horizon": "5yr",
        "likelihood": "possible",
    },
    {
        "id": "s_compat",
        "title": "Compat",
        "summary": "Compat scenario",
        "horizon": "1yr",
        "likelihood": "most_likely",
    },
]

MOCK_ACTIONS = {"actions": []}


def _mock_scenarios(extracted):
    async def inner():
        return MOCK_SCENARIOS

    return inner()


def _mock_actions(scenario, extracted):
    async def inner():
        return MOCK_ACTIONS

    return inner()


# Patch pipeline functions at module import time
import pipeline.scenario_gen as sg
import pipeline.action_planner as ap

sg.generate_scenarios = _mock_scenarios
ap.generate_actions = _mock_actions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STATE_FILE = Path(__file__).parent.parent.parent / "state" / "runtime_state.json"


def _reset_state():
    """Reset the runtime state to a clean state before each test."""
    from datetime import datetime, timezone

    clean_state = {
        "persona_id": "p05",
        "active_scenario": None,
        "archived_scenarios": [],
        "queue": [],
        "approvals": [],
        "workers": [
            {
                "worker_id": "kg_worker",
                "label": "KG Search",
                "status": "ready",
                "queue_depth": 0,
                "last_error": None,
            },
            {
                "worker_id": "calendar_worker",
                "label": "Calendar Scheduler",
                "status": "ready",
                "queue_depth": 0,
                "last_error": None,
            },
            {
                "worker_id": "notion_leads_worker",
                "label": "Notion Leads",
                "status": "ready",
                "queue_depth": 0,
                "last_error": None,
            },
            {
                "worker_id": "notion_opportunity_worker",
                "label": "Notion Opportunities",
                "status": "ready",
                "queue_depth": 0,
                "last_error": None,
            },
            {
                "worker_id": "figma_worker",
                "label": "Figma Portfolio",
                "status": "ready",
                "queue_depth": 0,
                "last_error": None,
            },
            {
                "worker_id": "facebook_worker",
                "label": "Facebook Publisher",
                "status": "ready",
                "queue_depth": 0,
                "last_error": None,
            },
        ],
        "budgets": [
            {
                "worker_id": "kg_worker",
                "max_runtime_seconds": 60,
                "max_retries": 2,
                "max_queue_items": 10,
            },
            {
                "worker_id": "calendar_worker",
                "max_runtime_seconds": 60,
                "max_retries": 2,
                "max_queue_items": 10,
            },
            {
                "worker_id": "notion_leads_worker",
                "max_runtime_seconds": 60,
                "max_retries": 2,
                "max_queue_items": 10,
            },
            {
                "worker_id": "notion_opportunity_worker",
                "max_runtime_seconds": 60,
                "max_retries": 2,
                "max_queue_items": 10,
            },
            {
                "worker_id": "figma_worker",
                "max_runtime_seconds": 60,
                "max_retries": 2,
                "max_queue_items": 10,
            },
            {
                "worker_id": "facebook_worker",
                "max_runtime_seconds": 60,
                "max_retries": 2,
                "max_queue_items": 10,
            },
        ],
        "circuits": [
            {
                "worker_id": "kg_worker",
                "failure_streak": 0,
                "open_until": None,
                "last_error": None,
            },
            {
                "worker_id": "calendar_worker",
                "failure_streak": 0,
                "open_until": None,
                "last_error": None,
            },
            {
                "worker_id": "notion_leads_worker",
                "failure_streak": 0,
                "open_until": None,
                "last_error": None,
            },
            {
                "worker_id": "notion_opportunity_worker",
                "failure_streak": 0,
                "open_until": None,
                "last_error": None,
            },
            {
                "worker_id": "figma_worker",
                "failure_streak": 0,
                "open_until": None,
                "last_error": None,
            },
            {
                "worker_id": "facebook_worker",
                "failure_streak": 0,
                "open_until": None,
                "last_error": None,
            },
        ],
        "cycle_history": [],
        "event_history": [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    STATE_FILE.write_text(json.dumps(clean_state))


@pytest.fixture()
def client():
    _reset_state()
    with TestClient(app) as c:
        yield c


def _activate_scenario(client: TestClient) -> dict:
    """Activate a scenario via the legacy /api/agent/activate so we have state."""
    return client.post(
        "/api/agent/activate",
        json={
            "scenario_id": "s_test_v1",
            "scenario_title": "V1 Test Scenario",
            "scenario_summary": "scenario for v1 tests",
            "scenario_horizon": "5yr",
            "scenario_likelihood": "possible",
            "scenario_tags": ["test"],
        },
    ).json()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_v1_health(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "health"
    assert body["status"] == "ok"
    assert "livemode" in body


@pytest.mark.fast
def test_v1_health_test_mode(client):
    r = client.get("/v1/health", headers={"Authorization": "Bearer sk_test_demo"})
    assert r.status_code == 200
    assert r.json()["livemode"] is False


# ---------------------------------------------------------------------------
# Runtime (renamed /api/agent/state)
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_v1_runtime(client):
    r = client.get("/v1/runtime")
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "runtime"
    assert "workers" in body
    assert "queue" in body


# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_v1_workers_list(client):
    r = client.get("/v1/workers")
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "list"
    assert len(body["data"]) == 6
    for w in body["data"]:
        assert w["id"].startswith("wrkr_")
        assert w["object"] == "worker"


@pytest.mark.fast
def test_v1_workers_get_by_id(client):
    """Bug: GET /v1/workers/{id} should find a worker by its prefixed ID."""
    list_r = client.get("/v1/workers")
    first = list_r.json()["data"][0]
    wid = first["id"]

    r = client.get(f"/v1/workers/{wid}")
    assert r.status_code == 200
    assert r.json()["id"] == wid


@pytest.mark.fast
def test_v1_workers_map(client):
    r = client.get("/v1/workers/map")
    assert r.status_code == 200
    body = r.json()
    assert "nodes" in body
    assert "edges" in body


@pytest.mark.fast
def test_v1_workers_skills(client):
    r = client.get("/v1/workers/skills")
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "list"
    assert len(body["data"]) > 0


@pytest.mark.fast
def test_v1_workers_expand_skills(client):
    r = client.get("/v1/workers?expand[]=skills")
    assert r.status_code == 200
    body = r.json()
    # At least one worker should have skills expanded
    has_skills = any("skills" in w for w in body["data"])
    assert has_skills


# ---------------------------------------------------------------------------
# Quests — Bug: list returns quest but GET/{id} was 404
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_v1_quests_list_empty_initially(client):
    r = client.get("/v1/quests")
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "list"


@pytest.mark.fast
def test_v1_quests_list_after_activate(client):
    """After activating, GET /v1/quests should return a quest."""
    _activate_scenario(client)
    r = client.get("/v1/quests")
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) == 1
    quest = body["data"][0]
    assert quest["id"].startswith("qst_")
    assert quest["object"] == "quest"
    assert quest["status"] == "active"


@pytest.mark.fast
def test_v1_quests_get_by_id(client):
    """Bug fix: GET /v1/quests/{id} should return the quest, not 404."""
    _activate_scenario(client)
    list_r = client.get("/v1/quests")
    quest = list_r.json()["data"][0]
    qid = quest["id"]

    r = client.get(f"/v1/quests/{qid}")
    assert r.status_code == 200
    assert r.json()["id"] == qid


@pytest.mark.fast
def test_v1_quests_get_nonexistent(client):
    r = client.get("/v1/quests/qst_nonexistent")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "resource_missing"


@pytest.mark.fast
def test_v1_quests_stable_id(client):
    """Bug fix: quest ID should be deterministic — same scenario yields same quest ID."""
    _activate_scenario(client)
    r1 = client.get("/v1/quests")
    r2 = client.get("/v1/quests")
    assert r1.json()["data"][0]["id"] == r2.json()["data"][0]["id"]


# ---------------------------------------------------------------------------
# Approvals — Bug: list showed approvals but GET/{id} and resolve failed
# ---------------------------------------------------------------------------


def _create_approval(client: TestClient) -> str:
    """Enqueue a facebook publish_post to trigger an approval.

    Returns an unresolved approval ID. Handles state pollution from prior tests
    by tracking which approval IDs existed before the enqueue.
    """
    _activate_scenario(client)

    # Snapshot existing pending approval IDs so we can find the new one
    existing = {
        a["id"] for a in client.get("/v1/approvals?pending=true").json()["data"]
    }

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

    approvals = client.get("/v1/approvals?pending=true").json()["data"]
    # Prefer newly created approval, fall back to any pending one
    new = [a for a in approvals if a["id"] not in existing]
    pick = new[0] if new else (approvals[0] if approvals else None)
    assert pick is not None, "Expected at least one pending approval"
    return pick["id"]


@pytest.mark.fast
def test_v1_approvals_list(client):
    approval_id = _create_approval(client)
    r = client.get("/v1/approvals")
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "list"
    assert any(a["id"] == approval_id for a in body["data"])


@pytest.mark.fast
def test_v1_approvals_get_by_id(client):
    """Bug fix: GET /v1/approvals/{id} should find the approval using the same ID from list."""
    approval_id = _create_approval(client)
    r = client.get(f"/v1/approvals/{approval_id}")
    assert r.status_code == 200
    assert r.json()["id"] == approval_id


@pytest.mark.fast
def test_v1_approvals_resolve(client):
    """Bug fix: POST /v1/approvals/{id}/resolve should work with the ID from list."""
    approval_id = _create_approval(client)
    r = client.post(
        f"/v1/approvals/{approval_id}/resolve",
        json={"decision": "approved"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == approval_id
    assert body["decision"] == "approved"


@pytest.mark.fast
def test_v1_approvals_resolve_nonexistent(client):
    r = client.post(
        "/v1/approvals/apprv_nonexistent/resolve",
        json={"decision": "approved"},
    )
    assert r.status_code == 404


@pytest.mark.fast
def test_v1_approvals_pending_filter(client):
    approval_id = _create_approval(client)
    r = client.get("/v1/approvals?pending=true")
    assert r.status_code == 200
    assert all(a["decision"] is None for a in r.json()["data"])


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_v1_events_post(client):
    _activate_scenario(client)
    r = client.post(
        "/v1/events",
        json={"type": "test_ping", "payload": {"hello": "world"}},
        headers={"Idempotency-Key": "evt-test-1"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"].startswith("evt_")
    assert body["object"] == "event"


@pytest.mark.fast
def test_v1_events_list(client):
    _activate_scenario(client)
    r = client.get("/v1/events")
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "list"
    assert len(body["data"]) > 0
    for evt in body["data"]:
        assert evt["id"].startswith("evt_")


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_v1_idempotency_replay(client):
    """POST with same Idempotency-Key should return same response."""
    _activate_scenario(client)
    key = "idem-test-replay-001"
    r1 = client.post(
        "/v1/events",
        json={"type": "idem_test", "payload": {}},
        headers={"Idempotency-Key": key},
    )
    r2 = client.post(
        "/v1/events",
        json={"type": "idem_test", "payload": {}},
        headers={"Idempotency-Key": key},
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]
    assert r2.headers.get("idempotent-replayed") == "true"


# ---------------------------------------------------------------------------
# Prefixed IDs — verify new IDs use prefixes
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_prefixed_task_ids(client):
    """Bug fix: newly seeded tasks should have task_ prefix."""
    _activate_scenario(client)
    state = client.get("/v1/runtime").json()
    for task in state["queue"]:
        assert task["task_id"].startswith("task_"), (
            f"Task ID missing prefix: {task['task_id']}"
        )


@pytest.mark.fast
def test_prefixed_event_ids(client):
    """Bug fix: new events should have evt_ prefix."""
    _activate_scenario(client)
    state = client.get("/v1/runtime").json()
    for event in state["event_history"]:
        assert event["event_id"].startswith("evt_"), (
            f"Event ID missing prefix: {event['event_id']}"
        )


@pytest.mark.fast
def test_prefixed_approval_ids(client):
    """Bug fix: new approvals should have apprv_ prefix."""
    _create_approval(client)
    state = client.get("/v1/runtime").json()
    for approval in state["approvals"]:
        assert approval["approval_id"].startswith("apprv_"), (
            f"Approval ID missing prefix: {approval['approval_id']}"
        )


# ---------------------------------------------------------------------------
# Backward compatibility — legacy /api/* routes still work
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_backward_compat_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.fast
def test_backward_compat_agent_state(client):
    r = client.get("/api/agent/state")
    assert r.status_code == 200
    assert "workers" in r.json()


@pytest.mark.fast
def test_backward_compat_agent_map(client):
    r = client.get("/api/agent/map")
    assert r.status_code == 200
    assert "nodes" in r.json()


@pytest.mark.fast
def test_backward_compat_agent_skills(client):
    r = client.get("/api/agent/skills")
    assert r.status_code == 200
    body = r.json()
    assert "data" in body or "skills" in body


@pytest.mark.fast
def test_backward_compat_agent_activate(client):
    r = client.post(
        "/api/agent/activate",
        json={
            "scenario_id": "s_compat",
            "scenario_title": "Compat Test",
            "scenario_summary": "test",
            "scenario_horizon": "1yr",
            "scenario_likelihood": "possible",
            "scenario_tags": [],
        },
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


@pytest.mark.fast
def test_backward_compat_agent_events(client):
    _activate_scenario(client)
    r = client.post(
        "/api/agent/events",
        json={"type": "compat_test", "payload": {}},
    )
    assert r.status_code == 200
    body = r.json()
    assert "id" in body and body["id"].startswith("evt_")


@pytest.mark.fast
def test_backward_compat_agent_approve(client):
    """Legacy /api/agent/approve still works with prefixed approval IDs."""
    approval_id = _create_approval(client)
    r = client.post(
        "/api/agent/approve",
        json={"approval_id": approval_id, "decision": "rejected"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "id" in body or "decision" in body


# ---------------------------------------------------------------------------
# Structured errors
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_v1_error_format(client):
    """Structured errors should have the Stripe-like format."""
    r = client.get("/v1/quests/qst_doesnotexist")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body
    err = body["error"]
    assert err["type"] == "invalid_request_error"
    assert err["code"] == "resource_missing"
    assert "message" in err
    assert "doc_url" in err
