"""Persistent store for always-on runtime state."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from state.models import AgentRuntimeState, WorkerBudget, WorkerCircuitState, WorkerNode, default_worker_catalog


class JsonStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _default_state(self) -> AgentRuntimeState:
        workers = [WorkerNode(worker_id=wid, label=label) for wid, label in default_worker_catalog()]
        budgets = [WorkerBudget(worker_id=wid) for wid, _ in default_worker_catalog()]
        circuits = [WorkerCircuitState(worker_id=wid) for wid, _ in default_worker_catalog()]
        return AgentRuntimeState(
            workers=workers,
            budgets=budgets,
            circuits=circuits,
            updated_at=self._now(),
        )

    def load(self) -> AgentRuntimeState:
        if not self.path.exists():
            state = self._default_state()
            self.save(state)
            return state

        data = json.loads(self.path.read_text())
        return AgentRuntimeState(**data)

    def save(self, state: AgentRuntimeState) -> None:
        state.updated_at = self._now()
        self.path.write_text(json.dumps(state.model_dump(mode="json"), indent=2))
