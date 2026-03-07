from __future__ import annotations

import pytest


DEMO_HEADERS = {"Authorization": "Bearer sk_demo_default"}


@pytest.mark.fast
def test_irreversible_action_requires_approval_and_is_not_executed(client):
    client.post(
        "/v1/quests",
        json={"scenario_id": "scen_001", "persona_id": "p05"},
        headers=DEMO_HEADERS,
    )

    r = client.post(
        "/v1/events",
        json={
            "type": "manual_enqueue",
            "payload": {
                "enqueue": True,
                "worker_id": "facebook_worker",
                "action": "publish_post",
                "priority": 1,
                "task_payload": {"content": "hello"},
            },
        },
        headers=DEMO_HEADERS,
    )
    assert r.status_code == 200

    runtime = client.get("/v1/runtime", headers=DEMO_HEADERS).json()
    queue = runtime.get("queue", [])
    target = next((t for t in queue if t.get("worker_id") == "facebook_worker" and t.get("action") == "publish_post"), None)
    assert target is not None
    assert target.get("status") == "waiting_approval"

    approvals = runtime.get("approvals", [])
    assert any(a.get("worker_id") == "facebook_worker" for a in approvals)


@pytest.mark.fast
def test_policy_blocked_action_event_emitted(client):
    client.post(
        "/v1/quests",
        json={"scenario_id": "scen_001", "persona_id": "p05"},
        headers=DEMO_HEADERS,
    )
    client.post(
        "/v1/events",
        json={
            "type": "manual_enqueue",
            "payload": {
                "enqueue": True,
                "worker_id": "facebook_worker",
                "action": "reply_comment",
                "priority": 1,
                "task_payload": {"comment_id": "c1", "message": "Thanks"},
            },
        },
        headers=DEMO_HEADERS,
    )

    events = client.get("/v1/events", headers=DEMO_HEADERS).json().get("data", [])
    assert any(e.get("type") == "policy_blocked_action" for e in events)


@pytest.mark.fast
def test_figma_reply_requires_approval(client):
    client.post(
        "/v1/quests",
        json={"scenario_id": "scen_001", "persona_id": "p05"},
        headers=DEMO_HEADERS,
    )

    r = client.post(
        "/v1/events",
        json={
            "type": "manual_enqueue",
            "payload": {
                "enqueue": True,
                "worker_id": "figma_worker",
                "action": "reply_comment",
                "priority": 1,
                "task_payload": {
                    "file_key": "demo_file_123",
                    "comment_id": "fig_c_001",
                    "message": "Thanks!",
                },
            },
        },
        headers=DEMO_HEADERS,
    )
    assert r.status_code == 200

    runtime = client.get("/v1/runtime", headers=DEMO_HEADERS).json()
    target = next(
        (
            t
            for t in runtime.get("queue", [])
            if t.get("worker_id") == "figma_worker" and t.get("action") == "reply_comment"
        ),
        None,
    )
    assert target is not None
    assert target.get("status") == "waiting_approval"
    assert any(a.get("worker_id") == "figma_worker" for a in runtime.get("approvals", []))
