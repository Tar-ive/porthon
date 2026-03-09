"""Universal agent output schema — single deterministic envelope for all agent types."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DataSource(BaseModel):
    """What data informed this result — traceable provenance."""

    ref_id: str
    source_type: Literal["data_ref", "kg_entity", "kg_relation", "api_response", "user_input"]
    description: str


class ExecutionStep(BaseModel):
    """Trace of one phase in the agent lifecycle."""

    phase: Literal["plan", "execute", "verify", "retrieve", "classify"]
    status: Literal["success", "skipped", "error"]
    detail: str
    duration_ms: float | None = None


class AgentResult(BaseModel):
    """Universal envelope every agent returns to the orchestrator."""

    agent_name: str = Field(description="e.g. 'calendar_coach', 'kg_retriever'")
    agent_type: Literal["composio", "kg", "llm", "deterministic"]
    status: Literal["success", "partial", "error", "dry_run"]
    data: dict = Field(description="Agent-specific payload (CalendarPlan, KG context, etc.)")
    sources: list[DataSource] = []
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    quest_connection: str = ""
    execution_log: list[ExecutionStep] = []
    timestamp: str = Field(description="ISO 8601")
    error: str | None = None
