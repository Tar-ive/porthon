"""OutcomeCollector — collects real outcome data to measure quest completion.

Deterministic agent — no LLM needed. Uses Composio APIs to check if
actions were actually completed.
"""

from __future__ import annotations

import logging

from agents.composio_tools import execute_action
from agents.models import (
    ActionOutcome,
    PersonaConfig,
    QuestOutcome,
    QuestPlan,
)

logger = logging.getLogger(__name__)


class OutcomeCollector:
    """Collects outcome signals from external services."""

    async def collect(
        self,
        quest_plan: QuestPlan,
        persona_config: PersonaConfig,
    ) -> QuestOutcome:
        outcomes: list[ActionOutcome] = []

        # Check calendar events
        if quest_plan.calendar:
            for event in quest_plan.calendar.events:
                found = await self._check_calendar_event(
                    event.title, persona_config.composio_entity_id
                )
                outcomes.append(
                    ActionOutcome(
                        action_id=event.title,
                        completed=found,
                        evidence=f"cal_event_{'found' if found else 'missing'}",
                    )
                )

        # Check Notion pages
        if quest_plan.workspace:
            for page in quest_plan.workspace.pages:
                found = await self._check_notion_page(
                    page.title, persona_config.composio_entity_id
                )
                outcomes.append(
                    ActionOutcome(
                        action_id=page.title,
                        completed=found,
                        evidence=f"notion_page_{'found' if found else 'missing'}",
                    )
                )

        # Check social posts
        if quest_plan.content:
            for post in quest_plan.content.posts:
                # Social posts are harder to verify — mark as pending
                outcomes.append(
                    ActionOutcome(
                        action_id=f"post_{post.platform}_{post.scheduled_time}",
                        completed=False,
                        evidence="pending_verification",
                    )
                )

        total = len(outcomes)
        completed = sum(1 for o in outcomes if o.completed)
        completion_rate = completed / total if total > 0 else 0.0

        return QuestOutcome(
            quest_id=quest_plan.quest_title,
            scenario_id=(
                quest_plan.calendar.quest_connection
                if quest_plan.calendar
                else ""
            ),
            action_outcomes=outcomes,
            completion_rate=completion_rate,
            profile_score_delta={},
        )

    async def _check_calendar_event(
        self, title: str, entity_id: str | None
    ) -> bool:
        result = await execute_action(
            "GOOGLECALENDAR_FIND_EVENT",
            entity_id=entity_id,
            arguments={"q": title},
        )
        if result.get("dry_run"):
            return False
        return bool(result.get("result"))

    async def _check_notion_page(
        self, title: str, entity_id: str | None
    ) -> bool:
        result = await execute_action(
            "NOTION_SEARCH",
            entity_id=entity_id,
            arguments={"query": title},
        )
        if result.get("dry_run"):
            return False
        return bool(result.get("result"))
