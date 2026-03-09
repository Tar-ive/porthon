from __future__ import annotations

import pytest

import deepagent.workers.calendar_worker as calendar_worker_mod
from deepagent.workers.calendar_worker import CalendarWorker


@pytest.mark.fast
def test_build_create_event_params_for_focus_block():
    worker = CalendarWorker()

    primary, legacy, total_minutes = worker._build_create_event_params(
        title="Hyperfocus Sprint",
        description="Deep work",
        start="2026-03-09T09:00:00",
        end="2026-03-09T10:30:00",
        is_focus=True,
    )

    assert total_minutes == 90
    assert primary["event_duration_hour"] == 1
    assert primary["event_duration_minutes"] == 30
    assert primary["eventType"] == "focusTime"
    assert "focusTimeProperties" in primary
    assert primary["time_zone"] == "America/Chicago"
    assert legacy["timezone"] == "America/Chicago"
    assert legacy["end_datetime"] == "2026-03-09T10:30:00"


@pytest.mark.fast
@pytest.mark.asyncio
async def test_create_event_with_fallback_retries_legacy(monkeypatch):
    worker = CalendarWorker()
    calls: list[dict] = []

    async def _fake_execute_action(action_name: str, params: dict | None = None, **kwargs):
        calls.append({"action_name": action_name, "params": params or {}})
        assert action_name == "GOOGLECALENDAR_CREATE_EVENT"
        if len(calls) == 1:
            assert "event_duration_hour" in (params or {})
            return {"dry_run": True, "error": "Invalid params"}
        assert "end_datetime" in (params or {})
        return {"dry_run": False, "result": {"htmlLink": "https://calendar.google.com/event?eid=abc"}}

    monkeypatch.setattr(calendar_worker_mod, "execute_action", _fake_execute_action, raising=True)

    result, variant = await worker._create_event_with_fallback(
        primary_params={"summary": "x", "event_duration_hour": 1, "event_duration_minutes": 0},
        legacy_params={"summary": "x", "end_datetime": "2026-03-09T10:00:00"},
    )

    assert variant == "legacy"
    assert not result.get("dry_run")
    assert len(calls) == 2


@pytest.mark.fast
@pytest.mark.asyncio
async def test_check_conflict_action_returns_busy_windows(monkeypatch):
    worker = CalendarWorker()

    async def _fake_execute_action(action_name: str, params: dict | None = None, **kwargs):
        assert action_name == "GOOGLECALENDAR_FREE_BUSY_QUERY"
        return {
            "dry_run": False,
            "result": {
                "data": {
                    "calendars": {
                        "primary": {
                            "busy": [{"start": "2026-03-09T09:30:00Z", "end": "2026-03-09T10:00:00Z"}]
                        }
                    }
                }
            },
        }

    monkeypatch.setattr(calendar_worker_mod, "execute_action", _fake_execute_action, raising=True)

    result = await worker.execute(
        "check_conflict",
        {"start_time": "2026-03-09T09:00:00Z", "end_time": "2026-03-09T10:00:00Z"},
    )

    assert result.ok
    assert result.data["has_conflict"] is True
    assert len(result.data["busy_windows"]) == 1


@pytest.mark.fast
@pytest.mark.asyncio
async def test_create_block_stops_on_conflict(monkeypatch):
    worker = CalendarWorker()

    async def _fake_execute_action(action_name: str, params: dict | None = None, **kwargs):
        if action_name == "GOOGLECALENDAR_FREE_BUSY_QUERY":
            return {
                "dry_run": False,
                "result": {
                    "data": {
                        "calendars": {
                            "primary": {
                                "busy": [{"start": "2026-03-09T09:00:00Z", "end": "2026-03-09T10:00:00Z"}]
                            }
                        }
                    }
                },
            }
        raise AssertionError(f"Unexpected action call: {action_name}")

    monkeypatch.setattr(calendar_worker_mod, "execute_action", _fake_execute_action, raising=True)

    result = await worker.execute(
        "create_block",
        {
            "title": "Hyperfocus Block",
            "start_time": "2026-03-09T09:00:00Z",
            "end_time": "2026-03-09T10:00:00Z",
            "description": "Deep work",
        },
    )

    assert not result.ok
    assert "conflicts" in result.message.lower()


@pytest.mark.fast
@pytest.mark.asyncio
async def test_create_block_uses_fallback_and_verifies(monkeypatch):
    worker = CalendarWorker()
    create_calls = 0
    find_calls = 0

    async def _fake_execute_action(action_name: str, params: dict | None = None, **kwargs):
        nonlocal create_calls, find_calls
        params = params or {}

        if action_name == "GOOGLECALENDAR_FREE_BUSY_QUERY":
            return {
                "dry_run": False,
                "result": {"data": {"calendars": {"primary": {"busy": []}}}},
            }

        if action_name == "GOOGLECALENDAR_FIND_EVENT":
            find_calls += 1
            if find_calls == 1:
                return {"dry_run": False, "result": {"data": {"items": []}}}
            return {
                "dry_run": False,
                "result": {
                    "data": {
                        "items": [
                            {
                                "summary": "Hyperfocus Block",
                                "start": {"dateTime": "2026-03-09T09:00:00"},
                            }
                        ]
                    }
                },
            }

        if action_name == "GOOGLECALENDAR_CREATE_EVENT":
            create_calls += 1
            if create_calls == 1:
                assert params.get("eventType") == "focusTime"
                assert "focusTimeProperties" in params
                assert "event_duration_hour" in params
                return {"dry_run": True, "error": "Schema mismatch"}
            assert "end_datetime" in params
            return {
                "dry_run": False,
                "result": {"htmlLink": "https://calendar.google.com/event?eid=abc123"},
            }

        raise AssertionError(f"Unexpected action call: {action_name}")

    monkeypatch.setattr(calendar_worker_mod, "execute_action", _fake_execute_action, raising=True)

    result = await worker.execute(
        "create_block",
        {
            "title": "Hyperfocus Block",
            "start_time": "2026-03-09T09:00:00",
            "end_time": "2026-03-09T10:00:00",
            "description": "Attention sprint",
            "event_type": "focus_block",
        },
    )

    assert result.ok
    assert result.data.get("payload_variant") == "legacy"
    assert result.data.get("external_links", {}).get("calendar_event")
    assert create_calls == 2
    assert find_calls == 2
