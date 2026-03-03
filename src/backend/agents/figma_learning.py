"""FigmaLearning — generates design challenges tied to scenario skill requirements."""

from __future__ import annotations

from agents.base import BaseAgent
from agents.models import LearningPlan, QuestContext


class FigmaLearning(BaseAgent):
    name = "FigmaLearning"

    def __init__(self, context: QuestContext) -> None:
        super().__init__(context)
        self._scores = context.profile_scores

    def _build_prompt(self) -> str:
        profile = self.context.extracted_data.get("profile", {})
        scenario = self.context.scenario
        actions = self.context.action_plan.get("actions", [])
        actions_str = "\n".join(
            f"  - {a.get('action', '')}" for a in actions
        )

        return f"""Persona: {profile.get('name', 'User')}, {profile.get('job', '')}

Chosen scenario: "{scenario.get('title', '')}"
Summary: {scenario.get('summary', '')}
Tags: {', '.join(scenario.get('tags', []))}

Related actions:
{actions_str}

Profile scores:
- Growth: {self._scores.growth}
- Execution: {self._scores.execution}

Design rules:
- Growth > 0.5 + Execution < 0.5: Generate challenges that produce portfolio-worthy artifacts (not just exercises)
- Each challenge should simulate real client work tied to the scenario
- Include milestones with concrete deliverables

Return JSON:
{{
  "challenges": [
    {{
      "title": "challenge title",
      "brief": "detailed brief simulating real client work",
      "skill_focus": ["skill1", "skill2"],
      "difficulty": "beginner|intermediate|advanced",
      "estimated_hours": 4.0,
      "portfolio_worthy": true
    }}
  ],
  "milestones": [
    {{
      "title": "milestone title",
      "target_date": "Week 2",
      "deliverable": "what to produce",
      "linked_challenge": "challenge title or null"
    }}
  ],
  "weekly_practice_hours": 6.0,
  "portfolio_targets": ["target1", "target2"],
  "quest_connection": "how this learning plan supports the chosen scenario"
}}"""

    async def plan(self) -> dict:
        return await self._llm_json(
            system=(
                "You are a design learning coach. You create structured design challenges "
                "that produce portfolio-worthy work while building skills. Challenges should "
                "simulate real-world client projects. Return ONLY valid JSON."
            ),
            user=self._build_prompt(),
        )

    async def execute(self, plan: dict) -> dict:
        # FigmaLearning is LLM-only — no external API calls
        return plan

    def to_output(self, plan: dict) -> LearningPlan:
        return LearningPlan(**plan)
