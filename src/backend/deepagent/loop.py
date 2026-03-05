"""Always-on master loop service."""

from __future__ import annotations

import asyncio
import contextlib
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from deepagent.demo_artifacts import (
    build_facebook_watch_state,
    build_proactive_artifacts,
    make_draft_reply,
)
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

    def _seed_scenario_tasks(
        self,
        state: AgentRuntimeState,
        scenario: ActiveScenarioState,
        demo_mode: bool = False,
    ) -> None:
        seeded = [
            ("kg_worker", "search", 10),
            ("calendar_worker", "sync_schedule", 20),
            ("notion_leads_worker", "create_pipeline", 30),
            ("notion_opportunity_worker", "create_workspace", 30),
            ("facebook_worker", "draft_posts", 40),
            ("figma_worker", "generate_challenge", 40),
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
                    "scenario_summary": scenario.summary,
                    "horizon": scenario.horizon,
                    "query": f"Scenario context for {scenario.title}: {scenario.summary}",
                    "demo_mode": demo_mode,
                },
                created_at=created,
                updated_at=created,
            )
            state.queue.append(task)

    async def activate_scenario(
        self,
        scenario: dict[str, Any],
        demo_mode: bool = False,
    ) -> dict[str, Any]:
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
            if demo_mode:
                from pipeline.demo_theo import generate_value_signals

                state.value_signals = generate_value_signals(state.persona_id)
                state.demo_artifacts["proactive_preview"] = build_proactive_artifacts(
                    active.model_dump(mode="json")
                )
            self._seed_scenario_tasks(state, active, demo_mode=demo_mode)
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
        start = time.perf_counter()
        async with self._lock:
            state = self.store.load()
            event = await self._append_event(state, event_type="cycle_start", payload={"trigger": trigger})
            result = await self.dispatcher.dispatch_cycle(state)
            cycle_duration_ms = int((time.perf_counter() - start) * 1000)
            cycle_end = await self._append_event(
                state,
                event_type="cycle_end",
                payload={
                    "trigger": trigger,
                    "cycle_id": result["cycle_id"],
                    "executed": len(result["executed_tasks"]),
                    "failed": len(result["failed_tasks"]),
                    "approval_waiting": len(result["approval_waiting"]),
                    "cycle_duration_ms": cycle_duration_ms,
                },
            )
            self.store.save(state)

        await self.stream.publish(event)
        await self.stream.publish(cycle_end)
        result["cycle_duration_ms"] = cycle_duration_ms
        return result

    async def ingest_event(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        async with self._lock:
            state = self.store.load()
            event = await self._append_event(state, event_type=event_type, payload=payload)
            await self._handle_demo_event(state, event_type, payload)
            if payload.get("enqueue"):
                t = WorkerTask(
                    task_id=_prefixed_id("task_"),
                    worker_id=payload.get("worker_id", "kg_worker"),
                    action=payload.get("action", "search"),
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

    async def _handle_demo_event(
        self,
        state: AgentRuntimeState,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        if event_type == "demo.workflow.proactive.preview":
            active = state.active_scenario.model_dump(mode="json") if state.active_scenario else {}
            state.demo_artifacts["proactive_preview"] = build_proactive_artifacts(active)
            if not state.value_signals:
                from pipeline.demo_theo import generate_value_signals

                state.value_signals = generate_value_signals(state.persona_id)
            return

        if event_type == "demo.workflow.proactive.commit":
            await self._enqueue_proactive_commit(state, payload)
            return

        if event_type == "demo.workflow.facebook_watch.start":
            state.workflow_state["facebook_watch"] = build_facebook_watch_state(payload)
            state.demo_artifacts.setdefault("facebook_watch", {})
            state.demo_artifacts["facebook_watch"].setdefault("pending_replies", [])
            return

        if event_type == "demo.workflow.facebook_watch.inject":
            comments = payload.get("comments", [])
            scenario_title = (
                state.active_scenario.title if state.active_scenario else payload.get("scenario_title", "")
            )
            watch = state.demo_artifacts.setdefault("facebook_watch", {})
            pending = watch.setdefault("pending_replies", [])
            for c in comments:
                comment_id = c.get("comment_id", _prefixed_id("comment_"))
                pending.append(
                    {
                        "comment_id": comment_id,
                        "post_id": c.get("post_id", ""),
                        "from": c.get("from", {}),
                        "message": c.get("message", ""),
                        "draft_reply": make_draft_reply(c.get("message", ""), scenario_title),
                        "status": "ready_to_send",
                        "created_at": self._now_iso(),
                    }
                )
            return

        if event_type == "demo.workflow.facebook_watch.poll":
            await self._poll_facebook_watch(state, payload)

    async def _enqueue_proactive_commit(
        self,
        state: AgentRuntimeState,
        payload: dict[str, Any],
    ) -> None:
        created = self._now_iso()
        preview = state.demo_artifacts.get("proactive_preview") or {}
        calendar_events = preview.get("calendar", {}).get("events", [])[:4]
        base = self._now()

        for idx, ev in enumerate(calendar_events):
            start_dt = base.replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=idx)
            duration = int(ev.get("duration_minutes", 60))
            end_dt = start_dt + timedelta(minutes=duration)

            state.queue.append(
                WorkerTask(
                    task_id=_prefixed_id("task_"),
                    worker_id="calendar_worker",
                    action="create_block",
                    priority=15,
                    payload={
                        "title": ev.get("title", "Demo Block"),
                        "description": "Demo proactive workflow commit",
                        "start_time": start_dt.isoformat(),
                        "end_time": end_dt.isoformat(),
                        "demo_mode": True,
                    },
                    created_at=created,
                    updated_at=created,
                )
            )

        state.queue.append(
            WorkerTask(
                task_id=_prefixed_id("task_"),
                worker_id="notion_leads_worker",
                action="create_pipeline",
                priority=20,
                payload={"demo_mode": True},
                created_at=created,
                updated_at=created,
            )
        )
        state.queue.append(
            WorkerTask(
                task_id=_prefixed_id("task_"),
                worker_id="notion_opportunity_worker",
                action="create_workspace",
                priority=20,
                payload={
                    "scenario_title": state.active_scenario.title if state.active_scenario else "Questline",
                    "demo_mode": True,
                },
                created_at=created,
                updated_at=created,
            )
        )

        file_key = payload.get("figma_file_key", "")
        if file_key:
            state.queue.append(
                WorkerTask(
                    task_id=_prefixed_id("task_"),
                    worker_id="figma_worker",
                    action="comment_file",
                    priority=25,
                    payload={
                        "file_key": file_key,
                        "message": "Demo workflow milestone: proactive quest commit executed.",
                        "demo_mode": True,
                    },
                    created_at=created,
                    updated_at=created,
                )
            )

    async def _poll_facebook_watch(
        self,
        state: AgentRuntimeState,
        payload: dict[str, Any],
    ) -> None:
        from deepagent.workers.facebook_worker import FacebookWorker

        cfg = state.workflow_state.get("facebook_watch")
        if not cfg:
            cfg = build_facebook_watch_state(payload)
            state.workflow_state["facebook_watch"] = cfg

        # Priority: poll payload override comments > stored demo_comments > live source.
        fetch_payload = dict(cfg)
        override_comments = payload.get("comments")
        if isinstance(override_comments, list):
            fetch_payload["comments"] = override_comments
        elif isinstance(cfg.get("demo_comments"), list) and cfg.get("demo_comments"):
            fetch_payload["demo_comments"] = cfg.get("demo_comments", [])

        worker = FacebookWorker()
        fetch = await worker.execute("fetch_comments", fetch_payload)
        if not fetch.ok:
            return

        seen = set(cfg.get("seen_comment_ids", []))
        comments = fetch.data.get("comments", [])
        new_comments = [c for c in comments if c.get("comment_id") and c["comment_id"] not in seen]

        watch = state.demo_artifacts.setdefault("facebook_watch", {})
        pending = watch.setdefault("pending_replies", [])
        scenario_title = state.active_scenario.title if state.active_scenario else ""

        for c in new_comments:
            draft = await worker.execute(
                "draft_comment_reply",
                {
                    "comment_text": c.get("message", ""),
                    "scenario_title": scenario_title,
                    "demo_mode": bool(cfg.get("demo_mode")),
                },
            )
            draft_text = draft.data.get("reply_text", make_draft_reply(c.get("message", ""), scenario_title))
            pending.append(
                {
                    "comment_id": c.get("comment_id"),
                    "post_id": c.get("post_id", ""),
                    "from": c.get("from", {}),
                    "message": c.get("message", ""),
                    "draft_reply": draft_text,
                    "status": "ready_to_send",
                    "created_at": self._now_iso(),
                }
            )
            seen.add(c.get("comment_id"))
            await self._append_event(
                state,
                event_type="facebook_comment_received",
                payload={
                    "comment_id": c.get("comment_id"),
                    "post_id": c.get("post_id", ""),
                    "message": c.get("message", ""),
                },
            )

        cfg["seen_comment_ids"] = sorted(seen)
        cfg["last_polled_at"] = self._now_iso()

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
