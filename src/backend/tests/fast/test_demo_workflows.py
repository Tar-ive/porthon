from __future__ import annotations

import pytest

from deepagent.workers.base import BaseWorker
from deepagent.workers.llm_schemas import (
    CalendarPlanLLM,
    FigmaCollabDeltaLLM,
    FigmaFollowupDraftLLM,
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

        if "Figma collaboration analyst" in system:
            return FigmaCollabDeltaLLM(
                summary="Collaborator requested tighter CTA emphasis and hierarchy cleanup.",
                next_action="Apply CTA hierarchy pass and post before/after frame.",
                severity="medium",
            ).model_dump(mode="json")

        if "draft concise Figma follow-up comments" in system:
            return FigmaFollowupDraftLLM(
                draft_comment="Great catch. I will apply a CTA hierarchy pass and share an updated frame shortly."
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

    monkeypatch.setattr(BaseWorker, "_llm_json", _fake_llm_json, raising=True)

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
    assert len(preview.get("notion_leads", {}).get("leads", [])) == 3
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
def test_demo_workflow_figma_watch_webhook_offline_llm_boundary(
    client, mock_offline_llm_and_tools
):
    _activate_demo_quest(client)

    r_start = client.post(
        "/v1/events",
        json={
            "type": "demo.workflow.figma_watch.start",
            "payload": {
                "file_key": "demo_file_123",
                "demo_mode": False,
            },
        },
        headers=DEMO_HEADERS,
    )
    assert r_start.status_code == 200

    webhook_payload = {
        "id": "wh_001",
        "event_id": "wh_001",
        "comment_id": "fig_c_001",
        "file_key": "demo_file_123",
        "message": "Can we tighten CTA hierarchy in this frame?",
        "from": {"name": "Design Peer"},
        "created_at": "2026-03-09T10:00:00Z",
    }
    r_webhook = client.post(
        "/v1/integrations/composio/webhook",
        json=webhook_payload,
        headers=DEMO_HEADERS,
    )
    assert r_webhook.status_code == 200

    runtime = client.get("/v1/runtime", headers=DEMO_HEADERS).json()
    watch_state = runtime.get("workflow_state", {}).get("figma_watch", {})
    assert watch_state
    assert watch_state.get("demo_mode") is False

    pending = runtime.get("demo_artifacts", {}).get("figma_watch", {}).get("pending_items", [])
    assert len(pending) == 1
    first = pending[0]
    assert first.get("comment_id") == "fig_c_001"
    assert first.get("status") == "ready_to_send"
    assert bool(str(first.get("draft_reply", "")).strip())
    assert bool(str(first.get("summary", "")).strip())

    before_count = len(pending)
    r_webhook_again = client.post(
        "/v1/integrations/composio/webhook",
        json=webhook_payload,
        headers=DEMO_HEADERS,
    )
    assert r_webhook_again.status_code == 200
    runtime_after = client.get("/v1/runtime", headers=DEMO_HEADERS).json()
    after_pending = runtime_after.get("demo_artifacts", {}).get("figma_watch", {}).get("pending_items", [])
    assert len(after_pending) == before_count

    events_body = client.get("/v1/events", headers=DEMO_HEADERS).json()
    assert any(e.get("type") == "figma_comment_received" for e in events_body.get("data", []))
    assert len(mock_offline_llm_and_tools) >= 1
