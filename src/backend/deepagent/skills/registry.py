"""Machine-readable skill registry for runtime and UI introspection."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SkillRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SkillActionDef(BaseModel):
    name: str
    risk: SkillRisk = SkillRisk.LOW
    required_params: list[str] = Field(default_factory=list)


class SkillDef(BaseModel):
    skill_id: str
    display_name: str
    description: str
    actions: list[SkillActionDef]


SKILL_REGISTRY: list[SkillDef] = [
    SkillDef(
        skill_id="kg-search",
        display_name="KG Search",
        description="Scenario-aware retrieval over personal memory and graph context.",
        actions=[
            SkillActionDef(name="search", required_params=["query"]),
            SkillActionDef(name="classify", required_params=["query"]),
        ],
    ),
    SkillDef(
        skill_id="calendar-scheduler",
        display_name="Calendar Scheduler",
        description="Calendar planning and adjustments for scenario execution.",
        actions=[
            SkillActionDef(name="sync_schedule"),
            SkillActionDef(name="create_block", risk=SkillRisk.MEDIUM, required_params=["start_time", "end_time", "title"]),
            SkillActionDef(name="move_block", risk=SkillRisk.MEDIUM, required_params=["start_time", "end_time", "title"]),
        ],
    ),
    SkillDef(
        skill_id="notion-leads-tracker",
        display_name="Notion Leads Tracker",
        description="Lead creation, progression, and follow-up management.",
        actions=[
            SkillActionDef(name="create_pipeline"),
            SkillActionDef(name="add_lead", required_params=["name"]),
            SkillActionDef(name="search_leads"),
        ],
    ),
    SkillDef(
        skill_id="notion-opportunity-tracker",
        display_name="Notion Opportunity Tracker",
        description="Opportunity forecasting and closure tracking.",
        actions=[
            SkillActionDef(name="create_workspace"),
            SkillActionDef(name="add_progress_page", required_params=["workspace_id", "title"]),
        ],
    ),
    SkillDef(
        skill_id="facebook-publisher",
        display_name="Facebook Publisher",
        description="Draft/schedule/publish scenario-aligned posts.",
        actions=[
            SkillActionDef(name="draft_posts"),
            SkillActionDef(name="fetch_comments", required_params=["page_id"]),
            SkillActionDef(name="draft_comment_reply", required_params=["comment_text"]),
            SkillActionDef(name="schedule_post", risk=SkillRisk.MEDIUM, required_params=["content", "scheduled_time"]),
            SkillActionDef(name="publish_post", risk=SkillRisk.HIGH, required_params=["content"]),
            SkillActionDef(name="reply_comment", risk=SkillRisk.HIGH, required_params=["comment_id", "message"]),
        ],
    ),
    SkillDef(
        skill_id="figma-plan-generator",
        display_name="Figma Plan Generator",
        description="Design challenge and milestone planning.",
        actions=[
            SkillActionDef(name="generate_challenge", required_params=["scenario_title"]),
            SkillActionDef(name="verify_connection"),
            SkillActionDef(name="comment_file", required_params=["file_key", "message"], risk=SkillRisk.MEDIUM),
        ],
    ),
    SkillDef(
        skill_id="self-improvement-loop",
        display_name="Self Improvement Loop",
        description="Log errors/learnings and promote recurring runtime improvements.",
        actions=[
            SkillActionDef(name="log_error", required_params=["summary"]),
            SkillActionDef(name="log_learning", required_params=["summary"]),
            SkillActionDef(name="log_feature_request", required_params=["summary"]),
            SkillActionDef(name="promote_pattern", risk=SkillRisk.MEDIUM, required_params=["summary"]),
        ],
    ),
]
