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
            SkillActionDef(name="retrieve_context", required_params=["intent", "scope", "query"]),
        ],
    ),
    SkillDef(
        skill_id="calendar-scheduler",
        display_name="Calendar Scheduler",
        description="Calendar planning and adjustments for scenario execution.",
        actions=[
            SkillActionDef(name="create_block", risk=SkillRisk.MEDIUM, required_params=["start_time", "end_time", "title"]),
            SkillActionDef(name="move_block", risk=SkillRisk.MEDIUM, required_params=["start_time", "end_time", "title"]),
            SkillActionDef(name="cancel_block", risk=SkillRisk.HIGH, required_params=["title"]),
            SkillActionDef(name="check_conflict", required_params=["start_time", "end_time"]),
        ],
    ),
    SkillDef(
        skill_id="notion-leads-tracker",
        display_name="Notion Leads Tracker",
        description="Lead creation, progression, and follow-up management.",
        actions=[
            SkillActionDef(name="create_lead", required_params=["lead_name"]),
            SkillActionDef(name="update_stage", required_params=["lead_name", "stage"]),
            SkillActionDef(name="log_touchpoint", required_params=["lead_name"]),
            SkillActionDef(name="set_followup", required_params=["lead_name", "due_date"]),
        ],
    ),
    SkillDef(
        skill_id="notion-opportunity-tracker",
        display_name="Notion Opportunity Tracker",
        description="Opportunity forecasting and closure tracking.",
        actions=[
            SkillActionDef(name="create_opportunity", required_params=["opportunity_name"]),
            SkillActionDef(name="update_probability", required_params=["opportunity_name", "probability_bucket"]),
            SkillActionDef(name="attach_next_action", required_params=["opportunity_name"]),
            SkillActionDef(name="close_won", risk=SkillRisk.MEDIUM, required_params=["opportunity_name"]),
            SkillActionDef(name="close_lost", risk=SkillRisk.MEDIUM, required_params=["opportunity_name"]),
        ],
    ),
    SkillDef(
        skill_id="facebook-publisher",
        display_name="Facebook Publisher",
        description="Draft/schedule/publish scenario-aligned posts.",
        actions=[
            SkillActionDef(name="draft_post", required_params=["content"]),
            SkillActionDef(name="schedule_post", risk=SkillRisk.MEDIUM, required_params=["content", "scheduled_time"]),
            SkillActionDef(name="publish_post", risk=SkillRisk.HIGH, required_params=["content"]),
            SkillActionDef(name="cancel_post", risk=SkillRisk.MEDIUM),
        ],
    ),
    SkillDef(
        skill_id="figma-plan-generator",
        display_name="Figma Plan Generator",
        description="Design challenge and milestone planning.",
        actions=[
            SkillActionDef(name="generate_plan", required_params=["scenario_title"]),
            SkillActionDef(name="derive_milestones", required_params=["scenario_title"]),
            SkillActionDef(name="sync_to_content", required_params=["scenario_title"]),
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
