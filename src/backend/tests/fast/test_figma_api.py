from __future__ import annotations

import pytest


DEMO_HEADERS = {"Authorization": "Bearer sk_demo_default"}


def _file_comment_payload(*, passcode: str, webhook_id: str, comment_id: str) -> dict:
    return {
        "event_type": "FILE_COMMENT",
        "passcode": passcode,
        "timestamp": "2026-03-09T10:00:00Z",
        "webhook_id": webhook_id,
        "comment_id": comment_id,
        "file_key": "demo_file_123",
        "file_name": "Demo File",
        "created_at": "2026-03-09T10:00:00Z",
        "triggered_by": {"id": "user_1", "handle": "design-peer"},
        "comment": [
            {"text": "Can we tighten CTA hierarchy"},
            {"text": " and spacing?"},
        ],
    }


@pytest.mark.fast
def test_figma_watchers_crud_demo(client):
    create = client.post(
        "/v1/figma/watchers",
        json={
            "file_key": "demo_file_123",
            "endpoint": "https://example.com/hooks/figma",
            "passcode": "pc_demo_123",
            "event_type": "FILE_COMMENT",
        },
        headers=DEMO_HEADERS,
    )
    assert create.status_code == 200
    watcher = create.json()
    watcher_id = watcher["id"]
    assert watcher["object"] == "figma_watcher"
    assert watcher["status"] == "ACTIVE"

    listed = client.get("/v1/figma/watchers", headers=DEMO_HEADERS)
    assert listed.status_code == 200
    assert any(w["id"] == watcher_id for w in listed.json()["data"])

    patched = client.patch(
        f"/v1/figma/watchers/{watcher_id}",
        json={"enabled": False},
        headers=DEMO_HEADERS,
    )
    assert patched.status_code == 200
    assert patched.json()["enabled"] is False
    assert patched.json()["status"] == "PAUSED"

    reqs = client.get(f"/v1/figma/watchers/{watcher_id}/requests", headers=DEMO_HEADERS)
    assert reqs.status_code == 200
    assert reqs.json()["object"] == "list"

    deleted = client.delete(f"/v1/figma/watchers/{watcher_id}", headers=DEMO_HEADERS)
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True


@pytest.mark.fast
def test_figma_webhook_file_comment_payload_normalized_and_deduped(client):
    create = client.post(
        "/v1/figma/watchers",
        json={
            "file_key": "demo_file_123",
            "endpoint": "https://example.com/hooks/figma",
            "passcode": "pc_demo_123",
            "event_type": "FILE_COMMENT",
        },
        headers=DEMO_HEADERS,
    )
    webhook_id = create.json()["webhook_id"]

    payload = _file_comment_payload(
        passcode="pc_demo_123",
        webhook_id=webhook_id,
        comment_id="fig_c_101",
    )
    first = client.post("/v1/figma/webhooks", json=payload, headers=DEMO_HEADERS)
    assert first.status_code == 200

    pending_first = client.get("/v1/figma/comments/pending", headers=DEMO_HEADERS).json()
    assert len(pending_first["data"]) == 1
    item = pending_first["data"][0]
    assert item["comment_id"] == "fig_c_101"
    assert item["message"] == "Can we tighten CTA hierarchy and spacing?"
    assert item["status"] == "ready_to_send"

    second = client.post("/v1/figma/webhooks", json=payload, headers=DEMO_HEADERS)
    assert second.status_code == 200
    pending_second = client.get("/v1/figma/comments/pending", headers=DEMO_HEADERS).json()
    assert len(pending_second["data"]) == 1


@pytest.mark.fast
def test_figma_prepare_send_enters_approval_flow(client):
    create = client.post(
        "/v1/figma/watchers",
        json={
            "file_key": "demo_file_123",
            "endpoint": "https://example.com/hooks/figma",
            "passcode": "pc_demo_123",
            "event_type": "FILE_COMMENT",
        },
        headers=DEMO_HEADERS,
    )
    webhook_id = create.json()["webhook_id"]

    payload = _file_comment_payload(
        passcode="pc_demo_123",
        webhook_id=webhook_id,
        comment_id="fig_c_202",
    )
    assert client.post("/v1/figma/webhooks", json=payload, headers=DEMO_HEADERS).status_code == 200

    prepare = client.post(
        "/v1/figma/comments/fig_c_202/prepare-send",
        json={"message": "Thanks, I will post the revised frame shortly."},
        headers=DEMO_HEADERS,
    )
    assert prepare.status_code == 200
    body = prepare.json()
    assert body["status"] == "awaiting_approval"
    assert bool(body.get("approval_id"))

    pending = client.get("/v1/figma/comments/pending", headers=DEMO_HEADERS).json()["data"]
    target = next(x for x in pending if x["comment_id"] == "fig_c_202")
    assert target["status"] == "awaiting_approval"
    assert target.get("approval_id") == body.get("approval_id")

    runtime = client.get("/v1/runtime", headers=DEMO_HEADERS).json()
    task = next(
        t
        for t in runtime.get("queue", [])
        if t.get("worker_id") == "figma_worker"
        and t.get("action") == "reply_comment"
        and t.get("payload", {}).get("comment_id") == "fig_c_202"
    )
    assert task["status"] == "waiting_approval"
    assert any(a.get("approval_id") == body.get("approval_id") for a in runtime.get("approvals", []))
