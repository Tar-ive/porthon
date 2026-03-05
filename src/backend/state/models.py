"""Runtime state contracts for always-on deep-agent execution."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class WorkerStatus(StrEnum):
    READY = "ready"
    RUNNING = "running"
    DEGRADED = "degraded"
    OPEN_CIRCUIT = "open_circuit"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_APPROVAL = "waiting_approval"


class ActiveScenarioState(BaseModel):
    scenario_id: str
    title: str
    horizon: str
    likelihood: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    activated_at: str
    created: int = 0
    metadata: dict[str, str] = Field(default_factory=dict)


class ArchivedScenarioState(ActiveScenarioState):
    archived_at: str


class WorkerBudget(BaseModel):
    worker_id: str
    max_runtime_seconds: int = 60
    max_retries: int = 2
    max_queue_items: int = 10


class WorkerCircuitState(BaseModel):
    worker_id: str
    failure_streak: int = 0
    open_until: str | None = None
    last_error: str | None = None


class WorkerTask(BaseModel):
    task_id: str
    worker_id: str
    action: str
    priority: int = 50
    payload: dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    retries: int = 0
    created_at: str
    updated_at: str
    created: int = 0
    metadata: dict[str, str] = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    approval_id: str
    task_id: str
    worker_id: str
    reason: str
    requested_at: str
    payload: dict[str, Any] = Field(default_factory=dict)
    resolved_at: str | None = None
    decision: str | None = None
    created: int = 0
    metadata: dict[str, str] = Field(default_factory=dict)


class CycleSnapshot(BaseModel):
    cycle_id: str
    trigger: str
    started_at: str
    finished_at: str | None = None
    executed_tasks: list[str] = Field(default_factory=list)
    failed_tasks: list[str] = Field(default_factory=list)


class WorkerNode(BaseModel):
    worker_id: str
    label: str
    status: WorkerStatus = WorkerStatus.READY
    queue_depth: int = 0
    last_error: str | None = None


class AgentRuntimeState(BaseModel):
    persona_id: str = "p05"
    active_scenario: ActiveScenarioState | None = None
    archived_scenarios: list[ArchivedScenarioState] = Field(default_factory=list)
    queue: list[WorkerTask] = Field(default_factory=list)
    approvals: list[ApprovalRequest] = Field(default_factory=list)
    workers: list[WorkerNode] = Field(default_factory=list)
    budgets: list[WorkerBudget] = Field(default_factory=list)
    circuits: list[WorkerCircuitState] = Field(default_factory=list)
    cycle_history: list[CycleSnapshot] = Field(default_factory=list)
    event_history: list[dict[str, Any]] = Field(default_factory=list)
    demo_artifacts: dict[str, Any] = Field(default_factory=dict)
    value_signals: dict[str, Any] = Field(default_factory=dict)
    workflow_state: dict[str, Any] = Field(default_factory=dict)
    updated_at: str


def default_worker_catalog() -> list[tuple[str, str]]:
    return [
        ("kg_worker", "KG Search"),
        ("calendar_worker", "Calendar Scheduler"),
        ("notion_leads_worker", "Notion Leads Tracker"),
        ("notion_opportunity_worker", "Notion Opportunity Tracker"),
        ("facebook_worker", "Facebook Publisher"),
        ("figma_worker", "Figma Plan Generator"),
    ]
