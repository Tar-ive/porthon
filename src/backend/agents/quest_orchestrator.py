"""QuestOrchestrator — decomposes action plan into agent tasks, runs all, assembles QuestPlan."""

from __future__ import annotations

import asyncio
import logging

from agents.base import BaseAgent
from agents.calendar_coach import CalendarCoach
from agents.content_creator import ContentCreator
from agents.figma_learning import FigmaLearning
from agents.models import QuestContext, QuestPlan
from agents.notion_organizer import NotionOrganizer

logger = logging.getLogger(__name__)

# Keywords that route actions to specific agents
_AGENT_KEYWORDS = {
    "calendar": ["schedule", "block", "time", "calendar", "meeting", "slot", "routine"],
    "figma": ["design", "portfolio", "figma", "ui", "ux", "visual", "prototype", "3d"],
    "notion": ["organize", "track", "database", "workspace", "pipeline", "template", "notion"],
    "content": ["post", "share", "publish", "content", "social", "brand", "public"],
}

# Which agents activate per archetype
_ARCHETYPE_AGENTS = {
    "emerging_talent": ["calendar", "figma", "notion", "content"],
    "reliable_operator": ["figma", "content"],  # already organized
    "at_risk": ["calendar", "notion"],  # stabilize basics
    "compounding_builder": ["content"],  # light touch
}


class QuestOrchestrator:
    """Coordinates all deep agents for a chosen questline."""

    def __init__(self, context: QuestContext) -> None:
        self.context = context

    def _select_agents(self) -> list[str]:
        """Determine which agents to activate based on archetype and action keywords."""
        archetype = self.context.profile_scores.archetype
        allowed = set(_ARCHETYPE_AGENTS.get(archetype, _ARCHETYPE_AGENTS["emerging_talent"]))

        # Also check action keywords to add agents if actions clearly need them
        actions_text = " ".join(
            a.get("action", "").lower()
            for a in self.context.action_plan.get("actions", [])
        )
        for agent_key, keywords in _AGENT_KEYWORDS.items():
            if any(kw in actions_text for kw in keywords):
                allowed.add(agent_key)

        return list(allowed)

    async def run(self) -> QuestPlan:
        """Run selected agents in parallel and assemble QuestPlan."""
        selected = self._select_agents()
        logger.info(f"[QuestOrchestrator] Selected agents: {selected}")

        agent_map: dict[str, BaseAgent] = {}
        if "calendar" in selected:
            agent_map["calendar"] = CalendarCoach(self.context)
        if "figma" in selected:
            agent_map["figma"] = FigmaLearning(self.context)
        if "notion" in selected:
            agent_map["notion"] = NotionOrganizer(self.context)
        if "content" in selected:
            agent_map["content"] = ContentCreator(self.context)

        # Run all agents concurrently with individual timeouts
        results: dict[str, dict] = {}
        if agent_map:
            tasks = {
                name: asyncio.wait_for(agent.run(), timeout=30.0)
                for name, agent in agent_map.items()
            }
            gathered = await asyncio.gather(
                *tasks.values(), return_exceptions=True
            )
            for name, result in zip(tasks.keys(), gathered):
                if isinstance(result, Exception):
                    logger.error(f"[QuestOrchestrator] {name} failed: {result}")
                    results[name] = {}
                else:
                    results[name] = result

        # Assemble QuestPlan
        scenario_title = self.context.scenario.get("title", "Quest")
        scenario_summary = self.context.scenario.get("summary", "")

        calendar_plan = None
        if "calendar" in results and results["calendar"]:
            try:
                calendar_plan = agent_map["calendar"].to_output(results["calendar"])  # type: ignore[union-attr]
            except Exception as e:
                logger.error(f"CalendarPlan parse error: {e}")

        learning_plan = None
        if "figma" in results and results["figma"]:
            try:
                learning_plan = agent_map["figma"].to_output(results["figma"])  # type: ignore[union-attr]
            except Exception as e:
                logger.error(f"LearningPlan parse error: {e}")

        workspace = None
        if "notion" in results and results["notion"]:
            try:
                workspace = agent_map["notion"].to_output(results["notion"])  # type: ignore[union-attr]
            except Exception as e:
                logger.error(f"NotionWorkspace parse error: {e}")

        content = None
        if "content" in results and results["content"]:
            try:
                content = agent_map["content"].to_output(results["content"])  # type: ignore[union-attr]
            except Exception as e:
                logger.error(f"ContentCalendar parse error: {e}")

        # Build execution summary
        executed = [name for name, r in results.items() if r]
        failed = [name for name, r in results.items() if not r]
        summary_parts = [f"Executed: {', '.join(executed)}"]
        if failed:
            summary_parts.append(f"Failed: {', '.join(failed)}")

        return QuestPlan(
            quest_title=scenario_title,
            quest_narrative=(
                f"Based on the '{scenario_title}' scenario: {scenario_summary}. "
                f"Agents activated: {', '.join(executed)}."
            ),
            calendar=calendar_plan,
            learning=learning_plan,
            workspace=workspace,
            content=content,
            execution_summary=". ".join(summary_parts),
            next_checkpoint="1 week from activation",
        )
