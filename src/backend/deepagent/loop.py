"""Always-on master loop service."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from deepagent.lead_os import (
    build_pod_snapshot,
    build_recommendations,
    ensure_lead_os_config,
    figma_actor_file_key,
    reconcile_leads,
    sustainability_snapshot,
)
from deepagent.demo_artifacts import (
    build_figma_watch_state,
    build_facebook_watch_state,
    build_proactive_artifacts,
    make_draft_reply,
)
from deepagent.dispatcher import Dispatcher
from deepagent.stream import StreamBroker
from integrations.notion_leads_service import get_notion_leads_service, normalize_lead_payload
from state.models import ActiveScenarioState, AgentRuntimeState, ArchivedScenarioState, TaskStatus, WorkerTask
from state.store import JsonStateStore

logger = logging.getLogger(__name__)


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
        notion_action = "sync_leads" if demo_mode else "ensure_pipeline"
        seeded = [
            ("kg_worker", "search", 10),
            ("calendar_worker", "sync_schedule", 20),
            ("notion_leads_worker", notion_action, 30),
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
            task_payload = {
                "scenario_id": scenario.scenario_id,
                "scenario_title": scenario.title,
                "scenario_summary": scenario.summary,
                "horizon": scenario.horizon,
                "query": f"Scenario context for {scenario.title}: {scenario.summary}",
                "demo_mode": demo_mode,
            }
            if demo_mode and worker_id == "notion_leads_worker" and action == "sync_leads":
                demo_leads = (
                    state.demo_artifacts
                    .get("proactive_preview", {})
                    .get("notion_leads", {})
                    .get("leads", [])
                )
                if isinstance(demo_leads, list) and demo_leads:
                    task_payload["leads"] = demo_leads[:20]
                task_payload["strict_reconcile"] = True

            task = WorkerTask(
                task_id=_prefixed_id("task_"),
                worker_id=worker_id,
                action=action,
                priority=priority,
                payload=task_payload,
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

        if event_type == "demo.workflow.figma_watch.start":
            state.workflow_state["figma_watch"] = build_figma_watch_state(payload)
            state.demo_artifacts.setdefault("figma_watch", {})
            state.demo_artifacts["figma_watch"].setdefault("pending_items", [])
            return

        if event_type == "demo.workflow.figma_watch.stop":
            cfg = state.workflow_state.get("figma_watch", {})
            if isinstance(cfg, dict):
                cfg["enabled"] = False
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
            return

        if event_type == "integration.figma.webhook.received":
            await self._handle_figma_webhook(state, payload)
            return

        if event_type == "integration.notion.webhook.received":
            await self._handle_notion_webhook(state, payload)
            return

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
                action="sync_leads",
                priority=20,
                payload={
                    "demo_mode": True,
                    "leads": preview.get("notion_leads", {}).get("leads", [])[:20],
                    "strict_reconcile": True,
                },
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
        state.queue.append(
            WorkerTask(
                task_id=_prefixed_id("task_"),
                worker_id="notion_opportunity_worker",
                action="add_progress_page",
                priority=23,
                payload={
                    "workspace_id": "demo_notion_workspace",
                    "title": "Progress: Next Actions",
                    "content_markdown": (
                        "1. Send one conversion-focused follow-up.\n\n"
                        "2. Complete one 45-minute admin sprint.\n\n"
                        "3. Ship one portfolio challenge milestone."
                    ),
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

    async def _handle_figma_webhook(
        self,
        state: AgentRuntimeState,
        payload: dict[str, Any],
    ) -> None:
        from deepagent.workers.figma_worker import FigmaWorker

        cfg = state.workflow_state.get("figma_watch")
        if not isinstance(cfg, dict):
            cfg = build_figma_watch_state(payload)
            state.workflow_state["figma_watch"] = cfg
        if cfg.get("enabled") is False:
            return

        raw_event_id = str(payload.get("event_id", "")).strip() or str(payload.get("id", "")).strip()
        file_key = str(payload.get("file_key", "")).strip()
        message = str(payload.get("message", "")).strip()
        comment_id = str(payload.get("comment_id", "")).strip()
        dedupe_key = comment_id or raw_event_id or f"{file_key}:{message}:{payload.get('created_at', '')}"
        if not dedupe_key:
            dedupe_key = _prefixed_id("evt_")

        seen = set(cfg.get("seen_event_ids", []))
        if dedupe_key in seen:
            return

        worker = FigmaWorker()
        scenario_title = state.active_scenario.title if state.active_scenario else ""
        result = await worker.execute(
            "process_webhook_event",
            {
                "event": payload,
                "scenario_title": scenario_title,
                "demo_mode": bool(cfg.get("demo_mode", True)),
            },
        )
        if not result.ok:
            return

        actor = payload.get("from", {}) if isinstance(payload.get("from", {}), dict) else {}
        actor_handle = str(actor.get("handle") or actor.get("id") or "").strip()
        item = {
            "event_id": result.data.get("event_id", dedupe_key),
            "comment_id": result.data.get("comment_id", comment_id),
            "file_key": result.data.get("file_key", file_key),
            "message": result.data.get("message", message),
            "summary": result.data.get("summary", ""),
            "next_action": result.data.get("next_action", ""),
            "draft_reply": result.data.get("draft_reply", ""),
            "status": result.data.get("status", "ready_to_send"),
            "created_at": self._now_iso(),
            "external_links": result.data.get("external_links", {}),
            "from": actor,
        }

        lead_os_cfg = state.workflow_state.get("lead_os", {})
        if isinstance(lead_os_cfg, dict):
            comment_links = lead_os_cfg.get("figma_comment_links", {})
            if not isinstance(comment_links, dict):
                comment_links = {}
            actor_links = lead_os_cfg.get("figma_actor_file_links", {})
            if not isinstance(actor_links, dict):
                actor_links = {}

            actor_key = figma_actor_file_key(item["file_key"], actor_handle)
            linked_lead_key = str(
                comment_links.get(item["comment_id"], "")
                or actor_links.get(actor_key, "")
            ).strip()
            if linked_lead_key:
                item["lead_key"] = linked_lead_key
                if item["comment_id"]:
                    comment_links[item["comment_id"]] = linked_lead_key
                lead_os_cfg["figma_comment_links"] = comment_links
                lead_os_cfg["figma_actor_file_links"] = actor_links
                state.workflow_state["lead_os"] = lead_os_cfg

        watch = state.demo_artifacts.setdefault("figma_watch", {})
        pending = watch.setdefault("pending_items", [])
        pending.append(item)

        links = state.demo_artifacts.setdefault("integration_links", {})
        figma_links = links.setdefault("figma", [])
        for link in item.get("external_links", {}).values():
            if isinstance(link, str) and link and link not in figma_links:
                figma_links.append(link)

        seen.add(dedupe_key)
        cfg["seen_event_ids"] = sorted(seen)
        cfg["last_event_at"] = self._now_iso()

        await self._append_event(
            state,
            event_type="figma_comment_received",
            payload={
                "event_id": item["event_id"],
                "comment_id": item["comment_id"],
                "file_key": item["file_key"],
            },
        )

    @staticmethod
    def _is_lead_relevant_notion_event(event_type: str, entity_type: str) -> bool:
        event_text = str(event_type or "").strip().lower()
        entity_text = str(entity_type or "").strip().lower()
        if event_text.startswith("page.") or event_text.startswith("data_source.") or event_text.startswith("database."):
            return True
        return entity_text in {"page", "data_source", "database"}

    async def _handle_notion_webhook(
        self,
        state: AgentRuntimeState,
        payload: dict[str, Any],
    ) -> None:
        cfg = state.workflow_state.get("notion_watch", {})
        if not isinstance(cfg, dict):
            cfg = {}
        stats = cfg.get("stats", {})
        if not isinstance(stats, dict):
            stats = {}

        event_id = str(payload.get("event_id") or payload.get("id") or "").strip()
        event_type = str(payload.get("event_type") or payload.get("type") or "").strip()
        entity_type = str(payload.get("entity_type", "")).strip()
        relevant = bool(payload.get("relevant"))
        if not relevant:
            relevant = self._is_lead_relevant_notion_event(event_type, entity_type)
        if not relevant:
            stats["ignored"] = int(stats.get("ignored", 0)) + 1
            cfg["stats"] = stats
            cfg["last_event_id"] = event_id
            cfg["last_event_type"] = event_type
            cfg["last_event_at"] = self._now_iso()
            state.workflow_state["notion_watch"] = cfg
            return

        workspace = state.workflow_state.get("notion_leads", {})
        if not isinstance(workspace, dict):
            workspace = {}
        data_source_id = str(
            workspace.get("data_source_id")
            or os.environ.get("NOTION_DATA_SOURCE_ID")
            or os.environ.get("NOTION_LEADS_DATA_SOURCE_ID")
            or ""
        ).strip()
        if not data_source_id:
            stats["skipped_missing_workspace"] = int(stats.get("skipped_missing_workspace", 0)) + 1
            cfg["stats"] = stats
            cfg["last_error"] = "notion_leads workspace not configured"
            cfg["last_event_id"] = event_id
            cfg["last_event_type"] = event_type
            cfg["last_event_at"] = self._now_iso()
            state.workflow_state["notion_watch"] = cfg
            return

        service = get_notion_leads_service()
        if not service.is_configured():
            stats["skipped_unconfigured"] = int(stats.get("skipped_unconfigured", 0)) + 1
            cfg["stats"] = stats
            cfg["last_error"] = "NOTION_INTEGRATION_SECRET not configured"
            cfg["last_event_id"] = event_id
            cfg["last_event_type"] = event_type
            cfg["last_event_at"] = self._now_iso()
            state.workflow_state["notion_watch"] = cfg
            return

        try:
            rows = await service.list_leads(data_source_id)
            leads = [normalize_lead_payload(item) for item in rows if isinstance(item, dict)]
            now_iso = self._now_iso()
            lead_os_cfg = ensure_lead_os_config(
                state.workflow_state.get("lead_os", {}),
                persona_id=str(state.persona_id),
                now_iso=now_iso,
            )
            lead_os_cfg = reconcile_leads(lead_os_cfg, leads, now_iso=now_iso)
            recommendations = build_recommendations(lead_os_cfg, top_n=12)
            runtime_queue = [task.model_dump(mode="json") for task in state.queue]
            lead_os_cfg["recommended_actions"] = recommendations
            lead_os_cfg["pods"] = build_pod_snapshot(lead_os_cfg, recommendations, runtime_queue)
            lead_os_cfg["sustainability"] = sustainability_snapshot(lead_os_cfg)
            lead_os_cfg["last_tick_at"] = now_iso
            lead_os_cfg["last_notion_event_id"] = event_id
            lead_os_cfg["updated_at"] = now_iso
            state.workflow_state["lead_os"] = lead_os_cfg

            stats["processed"] = int(stats.get("processed", 0)) + 1
            cfg["stats"] = stats
            cfg["last_processed_at"] = now_iso
            cfg["last_processed_event_id"] = event_id
            cfg["last_event_id"] = event_id
            cfg["last_event_type"] = event_type
            cfg["last_event_at"] = now_iso
            cfg["last_error"] = None
            state.workflow_state["notion_watch"] = cfg

            await self._append_event(
                state,
                event_type="notion_leads_refreshed",
                payload={
                    "event_id": event_id,
                    "event_type": event_type,
                    "lead_count": len(leads),
                    "recommended_count": len(recommendations),
                },
            )
        except Exception as exc:  # noqa: BLE001
            stats["refresh_errors"] = int(stats.get("refresh_errors", 0)) + 1
            cfg["stats"] = stats
            cfg["last_error"] = f"{type(exc).__name__}: {exc}"
            cfg["last_error_type"] = type(exc).__name__
            cfg["last_error_at"] = self._now_iso()
            cfg["last_event_id"] = event_id
            cfg["last_event_type"] = event_type
            cfg["last_event_at"] = self._now_iso()
            state.workflow_state["notion_watch"] = cfg
            logger.exception(
                "Notion webhook refresh failed event_id=%s event_type=%s data_source_id=%s",
                event_id,
                event_type,
                data_source_id,
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

    async def get_workflow_key(self, key: str) -> dict[str, Any]:
        async with self._lock:
            state = self.store.load()
            value = state.workflow_state.get(key, {})
            return value if isinstance(value, dict) else {}

    async def update_workflow_key(
        self,
        key: str,
        payload: dict[str, Any],
        merge: bool = True,
    ) -> dict[str, Any]:
        async with self._lock:
            state = self.store.load()
            current = state.workflow_state.get(key, {})
            if merge and isinstance(current, dict):
                merged = dict(current)
                merged.update(payload)
            else:
                merged = dict(payload)
            state.workflow_state[key] = merged
            self.store.save(state)
            return merged

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
            "tasks": [
                {
                    "task_id": t.task_id,
                    "worker_id": t.worker_id,
                    "action": t.action,
                    "status": t.status,
                    "result_summary": t.result_summary,
                    "external_links": t.external_links,
                    "updated_at": t.updated_at,
                }
                for t in state.queue[-30:]
            ],
            "workflow_state": state.workflow_state,
            "demo_artifacts": state.demo_artifacts,
            "updated_at": state.updated_at,
        }
