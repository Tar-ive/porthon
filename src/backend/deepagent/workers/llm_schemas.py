"""Typed schemas for deterministic worker LLM outputs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CalendarEventLLM(BaseModel):
    title: str
    description: str
    start_time: str
    end_time: str
    event_type: Literal[
        "focus_block", "admin", "body_doubling", "learning", "break", "review"
    ]
    adhd_note: str = ""

    model_config = {"extra": "forbid"}


class CalendarPlanLLM(BaseModel):
    events: list[CalendarEventLLM] = Field(default_factory=list)
    weekly_rhythm_summary: str
    adhd_accommodations: list[str] = Field(default_factory=list)
    quest_connection: str

    model_config = {"extra": "forbid"}


class FacebookPostLLM(BaseModel):
    platform: Literal["facebook"]
    content: str
    scheduled_unix: int
    post_type: Literal[
        "design_tip", "learning_in_public", "portfolio_piece", "personal_brand"
    ]
    hashtags: list[str] = Field(default_factory=list)
    linked_milestone: str | None = None

    model_config = {"extra": "forbid"}


class FacebookDraftPlanLLM(BaseModel):
    posts: list[FacebookPostLLM] = Field(default_factory=list)
    posting_cadence: str
    brand_voice_notes: str
    quest_connection: str

    model_config = {"extra": "forbid"}


class FacebookCommentReplyLLM(BaseModel):
    reply_text: str

    model_config = {"extra": "forbid"}


class FigmaChallengeLLM(BaseModel):
    title: str
    brief: str
    skill_focus: list[str] = Field(default_factory=list)
    difficulty: Literal["beginner", "intermediate", "advanced"]
    estimated_hours: float
    portfolio_worthy: bool

    model_config = {"extra": "forbid"}


class FigmaMilestoneLLM(BaseModel):
    title: str
    target_date: str
    deliverable: str
    linked_challenge: str | None = None

    model_config = {"extra": "forbid"}


class FigmaPlanLLM(BaseModel):
    challenges: list[FigmaChallengeLLM] = Field(default_factory=list)
    milestones: list[FigmaMilestoneLLM] = Field(default_factory=list)
    weekly_practice_hours: float
    portfolio_targets: list[str] = Field(default_factory=list)
    quest_connection: str

    model_config = {"extra": "forbid"}


class FigmaCollabDeltaLLM(BaseModel):
    summary: str
    next_action: str
    severity: Literal["low", "medium", "high"] = "medium"

    model_config = {"extra": "forbid"}


class FigmaFollowupDraftLLM(BaseModel):
    draft_comment: str

    model_config = {"extra": "forbid"}
