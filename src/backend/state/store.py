"""Persistent store for always-on runtime state."""

from __future__ import annotations

import json
import tempfile
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

    def _hydrate_catalog(self, state: AgentRuntimeState) -> AgentRuntimeState:
        catalog = dict(default_worker_catalog())

        workers_by_id = {w.worker_id: w for w in state.workers}
        budgets_by_id = {b.worker_id: b for b in state.budgets}
        circuits_by_id = {c.worker_id: c for c in state.circuits}

        for worker_id, label in catalog.items():
            if worker_id not in workers_by_id:
                workers_by_id[worker_id] = WorkerNode(worker_id=worker_id, label=label)
            else:
                if not workers_by_id[worker_id].label:
                    workers_by_id[worker_id].label = label

            if worker_id not in budgets_by_id:
                budgets_by_id[worker_id] = WorkerBudget(worker_id=worker_id)
            if worker_id not in circuits_by_id:
                circuits_by_id[worker_id] = WorkerCircuitState(worker_id=worker_id)

        state.workers = [workers_by_id[wid] for wid in catalog]
        state.budgets = [budgets_by_id[wid] for wid in catalog]
        state.circuits = [circuits_by_id[wid] for wid in catalog]
        return state

    def load(self) -> AgentRuntimeState:
        if not self.path.exists():
            state = self._default_state()
            self.save(state)
            return state

        data = json.loads(self.path.read_text())
        state = AgentRuntimeState(**data)
        if not state.budgets:
            state.budgets = [WorkerBudget(worker_id=wid) for wid, _ in default_worker_catalog()]
        if not state.circuits:
            state.circuits = [WorkerCircuitState(worker_id=wid) for wid, _ in default_worker_catalog()]
        if not state.workers:
            state.workers = [WorkerNode(worker_id=wid, label=label) for wid, label in default_worker_catalog()]
        return self._hydrate_catalog(state)

    def save(self, state: AgentRuntimeState) -> None:
        state.updated_at = self._now()
        content = json.dumps(state.model_dump(mode="json"), indent=2)
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=str(self.path.parent),
            prefix=f"{self.path.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        tmp_path.replace(self.path)
