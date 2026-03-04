from __future__ import annotations

from pathlib import Path

import pytest

from deepagent.loop import AlwaysOnMaster
from state.models import TaskStatus


@pytest.mark.fast
@pytest.mark.asyncio
async def test_activate_scenario_seeds_queue(tmp_path: Path):
    master = AlwaysOnMaster(state_path=tmp_path / "runtime_state.json", tick_seconds=900)
    await master.start()

    result = await master.activate_scenario(
        {
            "id": "s_demo",
            "title": "Demo Scenario",
            "summary": "test",
            "horizon": "1yr",
            "likelihood": "most_likely",
            "tags": ["demo"],
        }
    )

    state = await master.get_state()
    assert result["ok"] is True
    assert state["active_scenario"]["scenario_id"] == "s_demo"
    assert len(state["queue"]) >= 6

    await master.stop()


@pytest.mark.fast
@pytest.mark.asyncio
async def test_ingest_event_enqueues_and_runs_cycle(tmp_path: Path):
    master = AlwaysOnMaster(state_path=tmp_path / "runtime_state.json", tick_seconds=900)
    await master.start()

    await master.activate_scenario(
        {
            "id": "s_demo",
            "title": "Demo Scenario",
            "summary": "test",
            "horizon": "1yr",
            "likelihood": "most_likely",
            "tags": ["demo"],
        }
    )

    event_result = await master.ingest_event(
        "user_ping",
        {
            "enqueue": True,
            "worker_id": "kg_worker",
            "action": "refresh_context",
            "priority": 5,
        },
    )

    state = await master.get_state()
    assert event_result["ok"] is True
    assert any(t["status"] in {TaskStatus.COMPLETED, TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL} for t in state["queue"])
    assert len(state["cycle_history"]) >= 1

    await master.stop()


@pytest.mark.fast
@pytest.mark.asyncio
async def test_facebook_publish_goes_to_approval(tmp_path: Path):
    master = AlwaysOnMaster(state_path=tmp_path / "runtime_state.json", tick_seconds=900)
    await master.start()
    await master.activate_scenario(
        {
            "id": "s_demo",
            "title": "Demo Scenario",
            "summary": "test",
            "horizon": "1yr",
            "likelihood": "possible",
            "tags": [],
        }
    )

    await master.ingest_event(
        "manual_enqueue",
        {
            "enqueue": True,
            "worker_id": "facebook_worker",
            "action": "publish_post",
            "priority": 1,
            "task_payload": {"content": "hello"},
        },
    )

    state = await master.get_state()
    assert len(state["approvals"]) >= 1
    assert any(t["status"] == TaskStatus.WAITING_APPROVAL for t in state["queue"])

    approval_id = state["approvals"][0]["approval_id"]
    resolved = await master.resolve_approval(approval_id, "approved")
    assert resolved["ok"] is True
    assert resolved["decision"] == "approved"

    await master.stop()
