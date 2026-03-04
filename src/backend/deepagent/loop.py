"""Always-on master loop service."""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from deepagent.dispatcher import Dispatcher
from deepagent.stream import StreamBroker
from state.models import ActiveScenarioState, AgentRuntimeState, ArchivedScenarioState, TaskStatus, WorkerTask
from state.store import JsonStateStore


def _prefixed_id(prefix: str) -> str:
    return f"{prefix}{uuid4()}"


class AlwaysOnMaster:
    def __init__(self, state_path: Path, tick_seconds: int = 900) -> None:
        self.store = JsonStateStore(state_path)
        self.dispatcher = Dispatcher()
        self.stream = StreamBroker()
        self.tick_seconds = tick_seconds
        self._lock = asyncio.Lock()
        self._tick_task: asyncio.Task | None = None
        self._running = False

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _now_iso(self) -> str:
        return self._now().isoformat()

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._tick_task = asyncio.create_task(self._tick_loop(), name="always-on-master-tick")

    async def stop(self) -> None:
        self._running = False
        if self._tick_task and not self._tick_task.done():
            self._tick_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._tick_task

    async def _tick_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.tick_seconds)
            await self.run_cycle(trigger="tick")

    async def _append_event(self, state: AgentRuntimeState, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        event = {
            "event_id": _prefixed_id("evt_"),
            "type": event_type,
            "payload": payload,
            "created_at": self._now_iso(),
        }
        state.event_history = (state.event_history + [event])[-100:]
        return event

    def _seed_scenario_tasks(self, state: AgentRuntimeState, scenario: ActiveScenarioState) -> None:
        seeded = [
            ("kg_worker", "refresh_context", 10),
            ("calendar_worker", "sync_schedule", 20),
            ("notion_leads_worker", "sync_leads", 30),
            ("notion_opportunity_worker", "sync_opportunities", 30),
            ("facebook_worker", "draft_post", 40),
            ("figma_worker", "generate_plan", 40),
        ]
        created = self._now_iso()

        # Keep waiting approval tasks from previous cycle but clear stale pending/running tasks.
        state.queue = [
            t for t in state.queue if t.status == TaskStatus.WAITING_APPROVAL
        ]

        for worker_id, action, priority in seeded:
            task = WorkerTask(
                task_id=_prefixed_id("task_"),
                worker_id=worker_id,
                action=action,
                priority=priority,
                payload={
                    "scenario_id": scenario.scenario_id,
                    "scenario_title": scenario.title,
                    "horizon": scenario.horizon,
                },
                created_at=created,
                updated_at=created,
            )
            state.queue.append(task)

    async def activate_scenario(self, scenario: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            state = self.store.load()

            if state.active_scenario is not None:
                state.archived_scenarios.append(
                    ArchivedScenarioState(
                        **state.active_scenario.model_dump(mode="json"),
                        archived_at=self._now_iso(),
                    )
                )
                state.archived_scenarios = state.archived_scenarios[-20:]

            active = ActiveScenarioState(
                scenario_id=scenario.get("id", "unknown"),
                title=scenario.get("title", "Quest"),
                horizon=scenario.get("horizon", "5yr"),
                likelihood=scenario.get("likelihood", "possible"),
                summary=scenario.get("summary", ""),
                tags=scenario.get("tags", []),
                activated_at=self._now_iso(),
            )
            state.active_scenario = active
            self._seed_scenario_tasks(state, active)
            event = await self._append_event(
                state,
                event_type="scenario_activated",
                payload={"scenario_id": active.scenario_id, "title": active.title},
            )
            self.store.save(state)

        await self.stream.publish(event)
        cycle = await self.run_cycle(trigger="scenario_activated")
        return {
            "ok": True,
            "active_scenario": active.model_dump(mode="json"),
            "seeded_tasks": len([t for t in self.store.load().queue if t.status == TaskStatus.PENDING]),
            "cycle": cycle,
        }

    async def run_cycle(self, trigger: str = "event") -> dict[str, Any]:
        async with self._lock:
            state = self.store.load()
            event = await self._append_event(state, event_type="cycle_start", payload={"trigger": trigger})
            result = await self.dispatcher.dispatch_cycle(state)
            cycle_end = await self._append_event(
                state,
                event_type="cycle_end",
                payload={
                    "trigger": trigger,
                    "cycle_id": result["cycle_id"],
                    "executed": len(result["executed_tasks"]),
                    "failed": len(result["failed_tasks"]),
                    "approval_waiting": len(result["approval_waiting"]),
                },
            )
            self.store.save(state)

        await self.stream.publish(event)
        await self.stream.publish(cycle_end)
        return result

    async def ingest_event(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        async with self._lock:
            state = self.store.load()
            event = await self._append_event(state, event_type=event_type, payload=payload)
            if payload.get("enqueue"):
                t = WorkerTask(
                    task_id=_prefixed_id("task_"),
                    worker_id=payload.get("worker_id", "kg_worker"),
                    action=payload.get("action", "refresh_context"),
                    priority=int(payload.get("priority", 50)),
                    payload=payload.get("task_payload", {}),
                    created_at=self._now_iso(),
                    updated_at=self._now_iso(),
                )
                state.queue.append(t)
            self.store.save(state)

        await self.stream.publish(event)
        result = await self.run_cycle(trigger=event_type)
        return {"ok": True, "event": event, "cycle": result}

    async def resolve_approval(self, approval_id: str, decision: str) -> dict[str, Any]:
        decision = decision.lower().strip()
        if decision not in {"approved", "rejected"}:
            return {"ok": False, "error": "decision must be 'approved' or 'rejected'"}

        async with self._lock:
            state = self.store.load()
            approval = next((a for a in state.approvals if a.approval_id == approval_id and a.decision is None), None)
            if approval is None:
                return {"ok": False, "error": "approval not found"}

            approval.decision = decision
            approval.resolved_at = self._now_iso()

            task = next((t for t in state.queue if t.task_id == approval.task_id), None)
            if task is not None:
                task.updated_at = self._now_iso()
                task.status = TaskStatus.PENDING if decision == "approved" else TaskStatus.FAILED

            event = await self._append_event(
                state,
                event_type="approval_resolved",
                payload={"approval_id": approval_id, "decision": decision, "task_id": approval.task_id},
            )
            self.store.save(state)

        await self.stream.publish(event)
        cycle_result = None
        if decision == "approved":
            cycle_result = await self.run_cycle(trigger="approval")

        return {"ok": True, "approval_id": approval_id, "decision": decision, "cycle": cycle_result}

    async def get_state(self) -> dict[str, Any]:
        state = self.store.load()
        return state.model_dump(mode="json")

    async def get_map(self) -> dict[str, Any]:
        state = self.store.load()
        worker_queue: dict[str, int] = {}
        for task in state.queue:
            if task.status in {TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL}:
                worker_queue[task.worker_id] = worker_queue.get(task.worker_id, 0) + 1

        nodes = [
            {
                "id": "master",
                "label": "AlwaysOnMaster",
                "type": "master",
                "status": "running" if self._running else "stopped",
                "queue_depth": len([t for t in state.queue if t.status in {TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL}]),
            }
        ]
        for worker in state.workers:
            nodes.append(
                {
                    "id": worker.worker_id,
                    "label": worker.label,
                    "type": "worker",
                    "status": worker.status,
                    "queue_depth": worker_queue.get(worker.worker_id, 0),
                    "last_error": worker.last_error,
                }
            )

        edges = [{"from": "master", "to": worker["id"]} for worker in nodes if worker["id"] != "master"]

        return {
            "active_scenario": state.active_scenario.model_dump(mode="json") if state.active_scenario else None,
            "nodes": nodes,
            "edges": edges,
            "approvals": [a.model_dump(mode="json") for a in state.approvals if a.decision is None],
            "recent_events": state.event_history[-12:],
            "updated_at": state.updated_at,
        }
