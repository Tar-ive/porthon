"""Concurrent task dispatch for always-on master-worker runtime."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from deepagent.approval import requires_approval
from deepagent.workers import build_workers
from state.models import ApprovalRequest, AgentRuntimeState, CycleSnapshot, TaskStatus, WorkerStatus


def _prefixed_id(prefix: str) -> str:
    return f"{prefix}{uuid4()}"


class Dispatcher:
    def __init__(self) -> None:
        self.workers = build_workers()

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _now_iso(self) -> str:
        return self._now().isoformat()

    def _append_runtime_event(self, state: AgentRuntimeState, event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "event_id": _prefixed_id("evt_"),
            "type": event_type,
            "payload": payload,
            "created_at": self._now_iso(),
        }
        state.event_history = (state.event_history + [event])[-100:]

    async def dispatch_cycle(self, state: AgentRuntimeState, max_tasks: int = 12) -> dict[str, Any]:
        started_at = self._now_iso()
        cycle_id = _prefixed_id("cycle_")

        budget_by_worker = {b.worker_id: b for b in state.budgets}
        worker_by_id = {w.worker_id: w for w in state.workers}
        circuit_by_worker = {c.worker_id: c for c in state.circuits}

        pending = [t for t in state.queue if t.status == TaskStatus.PENDING]
        pending.sort(key=lambda t: (t.priority, t.created_at))
        scheduled = pending[:max_tasks]

        scheduled_for_exec = []
        approval_waiting: list[str] = []
        executed: list[str] = []
        failed: list[str] = []

        now = self._now()
        for task in scheduled:
            worker = worker_by_id.get(task.worker_id)
            circuit = circuit_by_worker.get(task.worker_id)
            if worker is None or circuit is None:
                continue

            if circuit.open_until:
                try:
                    open_until = datetime.fromisoformat(circuit.open_until)
                    if open_until > now:
                        worker.status = WorkerStatus.OPEN_CIRCUIT
                        continue
                except ValueError:
                    pass

            if requires_approval(task.worker_id, task.action):
                task.status = TaskStatus.WAITING_APPROVAL
                task.updated_at = self._now_iso()
                task.result_summary = "Blocked pending explicit approval (irreversible action)"
                task.error_code = "requires_approval"
                approval = ApprovalRequest(
                    approval_id=_prefixed_id("apprv_"),
                    task_id=task.task_id,
                    worker_id=task.worker_id,
                    reason=f"Action '{task.action}' requires approval",
                    requested_at=self._now_iso(),
                    payload=task.payload,
                )
                state.approvals.append(approval)
                approval_waiting.append(task.task_id)
                self._append_runtime_event(
                    state,
                    event_type="policy_blocked_action",
                    payload={
                        "task_id": task.task_id,
                        "worker_id": task.worker_id,
                        "action": task.action,
                        "reason": approval.reason,
                    },
                )
                continue

            task.status = TaskStatus.RUNNING
            task.updated_at = self._now_iso()
            worker.status = WorkerStatus.RUNNING
            scheduled_for_exec.append(task)

        async def _run_task(task):
            worker_impl = self.workers.get(task.worker_id)
            worker = worker_by_id[task.worker_id]
            circuit = circuit_by_worker[task.worker_id]
            budget = budget_by_worker[task.worker_id]

            if worker_impl is None:
                task.status = TaskStatus.FAILED
                task.updated_at = self._now_iso()
                task.finished_at = self._now_iso()
                worker.status = WorkerStatus.DEGRADED
                worker.last_error = "No worker implementation"
                task.result_summary = "Worker implementation missing"
                task.error_code = "worker_missing"
                failed.append(task.task_id)
                return

            try:
                result = await asyncio.wait_for(
                    worker_impl.execute(task.action, task.payload),
                    timeout=budget.max_runtime_seconds,
                )
                if result.approval_required:
                    task.status = TaskStatus.WAITING_APPROVAL
                    task.result_summary = "Worker requested approval"
                    task.error_code = "requires_approval"
                    approval = ApprovalRequest(
                        approval_id=_prefixed_id("apprv_"),
                        task_id=task.task_id,
                        worker_id=task.worker_id,
                        reason=result.approval_reason or f"Action '{task.action}' requires approval",
                        requested_at=self._now_iso(),
                        payload=task.payload,
                    )
                    state.approvals.append(approval)
                    approval_waiting.append(task.task_id)
                    worker.status = WorkerStatus.READY
                    self._append_runtime_event(
                        state,
                        event_type="policy_blocked_action",
                        payload={
                            "task_id": task.task_id,
                            "worker_id": task.worker_id,
                            "action": task.action,
                            "reason": approval.reason,
                        },
                    )
                    return

                if result.ok:
                    task.status = TaskStatus.COMPLETED
                    task.updated_at = self._now_iso()
                    task.finished_at = self._now_iso()
                    worker.status = WorkerStatus.READY
                    worker.last_error = None
                    circuit.failure_streak = 0
                    circuit.open_until = None
                    circuit.last_error = None
                    task.result_summary = result.message
                    links = result.data.get("external_links", {}) if isinstance(result.data, dict) else {}
                    task.external_links = links if isinstance(links, dict) else {}
                    task.error_code = None
                    executed.append(task.task_id)
                    return

                raise RuntimeError(result.message or "worker returned failure")
            except Exception as exc:  # noqa: BLE001
                task.retries += 1
                task.updated_at = self._now_iso()
                task.finished_at = self._now_iso()
                circuit.failure_streak += 1
                circuit.last_error = str(exc)
                worker.last_error = str(exc)
                task.result_summary = str(exc)
                task.error_code = "execution_error"

                if task.retries <= budget.max_retries:
                    task.status = TaskStatus.PENDING
                    worker.status = WorkerStatus.DEGRADED
                else:
                    task.status = TaskStatus.FAILED
                    failed.append(task.task_id)
                    worker.status = WorkerStatus.DEGRADED

                if circuit.failure_streak >= 3:
                    circuit.open_until = (self._now() + timedelta(minutes=5)).isoformat()
                    worker.status = WorkerStatus.OPEN_CIRCUIT

        if scheduled_for_exec:
            await asyncio.gather(*[_run_task(task) for task in scheduled_for_exec])

        for worker in state.workers:
            worker.queue_depth = len(
                [t for t in state.queue if t.worker_id == worker.worker_id and t.status in {TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL}]
            )

        state.cycle_history = (
            state.cycle_history
            + [
                CycleSnapshot(
                    cycle_id=cycle_id,
                    trigger="dispatch",
                    started_at=started_at,
                    finished_at=self._now_iso(),
                    executed_tasks=executed,
                    failed_tasks=failed,
                )
            ]
        )[-50:]

        return {
            "cycle_id": cycle_id,
            "executed_tasks": executed,
            "failed_tasks": failed,
            "approval_waiting": approval_waiting,
            "started_at": started_at,
            "finished_at": self._now_iso(),
        }
