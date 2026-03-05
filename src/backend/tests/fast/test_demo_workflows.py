from __future__ import annotations

import pytest

from deepagent.workers.base import BaseWorker
from deepagent.workers.llm_schemas import (
    CalendarPlanLLM,
    FacebookCommentReplyLLM,
    FacebookDraftPlanLLM,
    FigmaPlanLLM,
)

DEMO_HEADERS = {"Authorization": "Bearer sk_demo_default"}


def _activate_demo_quest(client) -> dict:
    resp = client.post(
        "/v1/quests",
        json={"scenario_id": "scen_001", "persona_id": "p05"},
        headers=DEMO_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body.get("activation_duration_ms"), int)
    return body


@pytest.fixture()
def mock_offline_llm_and_tools(monkeypatch):
    llm_calls: list[dict] = []

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("PORTTHON_OFFLINE_MODE", "0")

    async def _fake_llm_json(self, system: str, user: str):
        llm_calls.append({"worker_id": self.worker_id, "system": system, "user": user})

        if "design learning coach" in system:
            return FigmaPlanLLM(
                challenges=[
                    {
                        "title": "Offline LLM Figma Challenge",
                        "brief": "Deterministic brief from mocked LLM boundary.",
                        "skill_focus": ["layout", "hierarchy"],
                        "difficulty": "intermediate",
                        "estimated_hours": 4.0,
                        "portfolio_worthy": True,
                    }
                ],
                milestones=[
                    {
                        "title": "Week 1",
                        "target_date": "Week 1",
                        "deliverable": "Draft",
                        "linked_challenge": "Offline LLM Figma Challenge",
                    }
                ],
                weekly_practice_hours=6.0,
                portfolio_targets=["One polished challenge"],
                quest_connection="Supports quest execution.",
            ).model_dump(mode="json")

        if "draft concise, authentic Facebook replies" in system:
            return FacebookCommentReplyLLM(
                reply_text="Deterministic offline reply from mocked LLM boundary."
            ).model_dump(mode="json")

        if "personal brand content strategist" in system:
            return FacebookDraftPlanLLM(
                posts=[
                    {
                        "platform": "facebook",
                        "content": "Offline deterministic post.",
                        "scheduled_unix": 1773180000,
                        "post_type": "learning_in_public",
                        "hashtags": ["demo"],
                        "linked_milestone": "Milestone A",
                    }
                ],
                posting_cadence="1x per week",
                brand_voice_notes="Grounded and clear.",
                quest_connection="Supports scenario momentum.",
            ).model_dump(mode="json")

        if "ADHD-aware calendar coach" in system:
            return CalendarPlanLLM(
                events=[
                    {
                        "title": "Offline Focus Block",
                        "description": "Deterministic event.",
                        "start_time": "2026-03-09T09:00:00",
                        "end_time": "2026-03-09T10:00:00",
                        "event_type": "focus_block",
                        "adhd_note": "Mocked output",
                    }
                ],
                weekly_rhythm_summary="Simple weekly rhythm.",
                adhd_accommodations=["Short blocks"],
                quest_connection="Supports execution",
            ).model_dump(mode="json")

        return {}

    async def _fake_execute_action(*args, **kwargs):
        return {"dry_run": True, "result": {"data": {}}}

    import deepagent.workers.facebook_worker as fb_mod
    import deepagent.workers.figma_worker as fig_mod

    monkeypatch.setattr(BaseWorker, "_llm_json", _fake_llm_json, raising=True)
    monkeypatch.setattr(fb_mod, "execute_action", _fake_execute_action, raising=True)
    monkeypatch.setattr(fig_mod, "execute_action", _fake_execute_action, raising=True)

    return llm_calls


@pytest.mark.fast
def test_demo_workflow_proactive_preview_commit_offline_llm_boundary(
    client, mock_offline_llm_and_tools
):
    _activate_demo_quest(client)

    r_preview = client.post(
        "/v1/events",
        json={"type": "demo.workflow.proactive.preview", "payload": {}},
        headers=DEMO_HEADERS,
    )
    assert r_preview.status_code == 200

    runtime = client.get("/v1/runtime", headers=DEMO_HEADERS).json()
    preview = runtime.get("demo_artifacts", {}).get("proactive_preview", {})
    assert len(preview.get("calendar", {}).get("events", [])) == 4
    assert "notion_leads" in preview
    assert "notion_opportunity" in preview
    assert runtime.get("value_signals")

    r_commit = client.post(
        "/v1/events",
        json={
            "type": "demo.workflow.proactive.commit",
            "payload": {"figma_file_key": "demo_file_123"},
        },
        headers=DEMO_HEADERS,
    )
    assert r_commit.status_code == 200
    assert r_commit.json().get("cycle", {}).get("failed_tasks", []) == []

    r_enqueue = client.post(
        "/v1/events",
        json={
            "type": "manual_enqueue",
            "payload": {
                "enqueue": True,
                "worker_id": "figma_worker",
                "action": "generate_challenge",
                "priority": 1,
                "task_payload": {
                    "demo_mode": False,
                    "scenario_title": "Conversion-First Freelance Stabilization",
                },
            },
        },
        headers=DEMO_HEADERS,
    )
    assert r_enqueue.status_code == 200
    assert r_enqueue.json().get("cycle", {}).get("failed_tasks", []) == []
    assert len(mock_offline_llm_and_tools) >= 1

    events_body = client.get("/v1/events", headers=DEMO_HEADERS).json()
    cycle_ends = [e for e in events_body.get("data", []) if e.get("type") == "cycle_end"]
    assert cycle_ends
    assert any(
        isinstance(evt.get("payload", {}).get("cycle_duration_ms"), int)
        for evt in cycle_ends
    )


@pytest.mark.fast
def test_demo_workflow_facebook_watch_start_inject_poll_offline_llm_boundary(
    client, mock_offline_llm_and_tools
):
    _activate_demo_quest(client)

    r_start = client.post(
        "/v1/events",
        json={
            "type": "demo.workflow.facebook_watch.start",
            "payload": {
                "page_id": "me",
                "demo_mode": False,
                "demo_comments": [
                    {
                        "comment_id": "c_seed_001",
                        "post_id": "p_seed_001",
                        "message": "Seed comment one",
                    },
                    {
                        "comment_id": "c_seed_002",
                        "post_id": "p_seed_001",
                        "message": "Seed comment two",
                    },
                ],
            },
        },
        headers=DEMO_HEADERS,
    )
    assert r_start.status_code == 200

    r_inject = client.post(
        "/v1/events",
        json={
            "type": "demo.workflow.facebook_watch.inject",
            "payload": {
                "comments": [
                    {
                        "comment_id": "c_inject_001",
                        "post_id": "p_seed_001",
                        "message": "Injected comment",
                    }
                ]
            },
        },
        headers=DEMO_HEADERS,
    )
    assert r_inject.status_code == 200

    r_poll = client.post(
        "/v1/events",
        json={"type": "demo.workflow.facebook_watch.poll", "payload": {}},
        headers=DEMO_HEADERS,
    )
    assert r_poll.status_code == 200

    runtime = client.get("/v1/runtime", headers=DEMO_HEADERS).json()
    watch_state = runtime.get("workflow_state", {}).get("facebook_watch", {})
    assert watch_state
    assert watch_state.get("demo_mode") is False

    pending = (
        runtime.get("demo_artifacts", {})
        .get("facebook_watch", {})
        .get("pending_replies", [])
    )
    pending_ids = {p.get("comment_id") for p in pending}
    assert {"c_seed_001", "c_seed_002", "c_inject_001"}.issubset(pending_ids)
    assert all(p.get("status") == "ready_to_send" for p in pending)
    assert all(bool(str(p.get("draft_reply", "")).strip()) for p in pending)

    before_count = len(pending)
    r_poll_again = client.post(
        "/v1/events",
        json={"type": "demo.workflow.facebook_watch.poll", "payload": {}},
        headers=DEMO_HEADERS,
    )
    assert r_poll_again.status_code == 200
    runtime_after = client.get("/v1/runtime", headers=DEMO_HEADERS).json()
    after_pending = (
        runtime_after.get("demo_artifacts", {})
        .get("facebook_watch", {})
        .get("pending_replies", [])
    )
    assert len(after_pending) == before_count

    events_body = client.get("/v1/events", headers=DEMO_HEADERS).json()
    assert any(e.get("type") == "facebook_comment_received" for e in events_body.get("data", []))
    assert len(mock_offline_llm_and_tools) >= 1
