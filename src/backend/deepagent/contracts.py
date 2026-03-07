"""Pydantic I/O contracts for all deep-agent workers.

Moved from agents/models.py → deepagent/contracts.py
so the deep-agent runtime owns all its own contracts.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Profiling bridge
# ---------------------------------------------------------------------------

class ProfileScores(BaseModel):
    execution: float  # 0-1
    growth: float
    self_awareness: float
    financial_stress: float
    adhd_indicator: float
    archetype: Literal[
        "emerging_talent", "reliable_operator", "at_risk", "compounding_builder"
    ]
    deltas: dict[str, float] = {}


# ---------------------------------------------------------------------------
# Quest context (input to all workers)
# ---------------------------------------------------------------------------

class QuestContext(BaseModel):
    scenario: dict  # chosen scenario from pipeline
    action_plan: dict  # actions from pipeline
    profile_scores: ProfileScores
    extracted_data: dict  # raw extracted data with data_refs
    persona_id: str
    quest_memory: QuestMemory | None = None


# ---------------------------------------------------------------------------
# CalendarWorker I/O
# ---------------------------------------------------------------------------

class CalendarEvent(BaseModel):
    title: str
    description: str
    start_time: str
    end_time: str
    event_type: Literal[
        "focus_block", "admin", "body_doubling", "learning", "break", "review"
    ]
    adhd_note: str = ""
    linked_action_index: int | None = None


class CalendarPlan(BaseModel):
    events: list[CalendarEvent]
    weekly_rhythm_summary: str
    adhd_accommodations: list[str]
    quest_connection: str


# ---------------------------------------------------------------------------
# FigmaWorker I/O
# ---------------------------------------------------------------------------

class DesignChallenge(BaseModel):
    title: str
    brief: str
    skill_focus: list[str]
    difficulty: Literal["beginner", "intermediate", "advanced"]
    estimated_hours: float
    portfolio_worthy: bool


class LearningMilestone(BaseModel):
    title: str
    target_date: str
    deliverable: str
    linked_challenge: str | None = None


class LearningPlan(BaseModel):
    challenges: list[DesignChallenge]
    milestones: list[LearningMilestone]
    weekly_practice_hours: float
    portfolio_targets: list[str]
    quest_connection: str


# ---------------------------------------------------------------------------
# Notion Workers I/O
# ---------------------------------------------------------------------------

class NotionPage(BaseModel):
    title: str
    page_type: Literal["database", "page", "template"]
    parent: str | None = None
    properties: dict = {}
    content_markdown: str = ""


class NotionWorkspace(BaseModel):
    pages: list[NotionPage]
    setup_summary: str
    quest_connection: str


# ---------------------------------------------------------------------------
# Facebook Worker I/O
# ---------------------------------------------------------------------------

class ScheduledPost(BaseModel):
    platform: Literal["facebook", "instagram"]
    content: str
    scheduled_time: str
    post_type: Literal[
        "design_tip", "learning_in_public", "portfolio_piece", "personal_brand"
    ]
    hashtags: list[str] = []
    linked_milestone: str | None = None


class ContentCalendar(BaseModel):
    posts: list[ScheduledPost]
    posting_cadence: str
    brand_voice_notes: str
    quest_connection: str


# ---------------------------------------------------------------------------
# Continuous learning
# ---------------------------------------------------------------------------

class ActionOutcome(BaseModel):
    action_id: str
    completed: bool
    evidence: str
    completion_date: str | None = None
    notes: str = ""


class QuestOutcome(BaseModel):
    quest_id: str
    scenario_id: str
    action_outcomes: list[ActionOutcome]
    completion_rate: float
    profile_score_delta: dict[str, float] = {}


class QuestMemory(BaseModel):
    persona_id: str
    past_quests: list[QuestOutcome] = []
    learned_preferences: dict[str, str] = {}
    effective_patterns: list[str] = []
    ineffective_patterns: list[str] = []


# ---------------------------------------------------------------------------
# Orchestrator output (used by master loop)
# ---------------------------------------------------------------------------

class QuestPlan(BaseModel):
    quest_title: str
    quest_narrative: str
    calendar: CalendarPlan | None = None
    learning: LearningPlan | None = None
    workspace: NotionWorkspace | None = None
    content: ContentCalendar | None = None
    execution_summary: str
    next_checkpoint: str


# ---------------------------------------------------------------------------
# Multi-persona config
# ---------------------------------------------------------------------------

class PersonaConfig(BaseModel):
    persona_id: str
    data_dir: str
    composio_entity_id: str | None = None
    enabled_agents: list[str] = ["calendar", "figma", "notion", "content"]
    quest_memory_path: str = ""


# QuestContext needs QuestMemory which is defined after it, so we rebuild model
QuestContext.model_rebuild()
