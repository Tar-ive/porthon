"""ContentCreator — schedules social posts that track questline progress."""

from __future__ import annotations

from agents.base import BaseAgent
from agents.composio_tools import execute_action
from agents.models import ContentCalendar, QuestContext


class ContentCreator(BaseAgent):
    name = "ContentCreator"

    def __init__(self, context: QuestContext) -> None:
        super().__init__(context)
        self._scores = context.profile_scores

    def _build_prompt(self) -> str:
        profile = self.context.extracted_data.get("profile", {})
        scenario = self.context.scenario
        social = self.context.extracted_data.get("social", [])
        recent_posts = "\n".join(
            f"  - [{p.get('id', '')}] {p.get('text', '')[:100]}" for p in social[:3]
        )
        public_private_delta = self._scores.deltas.get("public_private", 0.0)

        return f"""Persona: {profile.get('name', 'User')}, {profile.get('job', '')}

Chosen scenario: "{scenario.get('title', '')}"
Summary: {scenario.get('summary', '')}

Recent social posts:
{recent_posts}

Profile scores:
- Growth: {self._scores.growth}
- Public/private persona delta: {public_private_delta}

Content rules:
- Public/private delta > 0.3: Create "learning in public" posts that authentically bridge the gap between public persona and private goals
- Align content schedule to questline milestones
- Content should demonstrate progress, not just announce intentions

Return JSON:
{{
  "posts": [
    {{
      "platform": "facebook|instagram",
      "content": "post content text",
      "scheduled_time": "Monday 10:00 AM",
      "post_type": "design_tip|learning_in_public|portfolio_piece|personal_brand",
      "hashtags": ["tag1"],
      "linked_milestone": "milestone title or null"
    }}
  ],
  "posting_cadence": "e.g. 2x per week",
  "brand_voice_notes": "guidance on tone and style",
  "quest_connection": "how this content plan supports the chosen scenario"
}}"""

    async def plan(self) -> dict:
        return await self._llm_json(
            system=(
                "You are a personal brand content strategist. You create authentic content "
                "calendars that bridge the gap between a user's public and private personas "
                "while tracking progress toward their chosen life scenario. Return ONLY valid JSON."
            ),
            user=self._build_prompt(),
        )

    async def execute(self, plan: dict) -> dict:
        posts = plan.get("posts", [])
        execution_results = []
        for post in posts:
            result = await execute_action(
                "FACEBOOK_CREATE_POST",
                arguments={
                    "content": post.get("content", ""),
                    "scheduled_time": post.get("scheduled_time", ""),
                },
            )
            execution_results.append(result)
        plan["execution_results"] = execution_results
        return plan

    def to_output(self, plan: dict) -> ContentCalendar:
        return ContentCalendar(**{k: v for k, v in plan.items() if k != "execution_results"})
