"""CalendarCoach — schedules ADHD-aware time blocks from the action plan."""

from __future__ import annotations

from agents.base import BaseAgent
from agents.composio_tools import execute_action
from agents.models import CalendarPlan, QuestContext


class CalendarCoach(BaseAgent):
    name = "CalendarCoach"

    def __init__(self, context: QuestContext) -> None:
        super().__init__(context)
        self._scores = context.profile_scores

    def _build_prompt(self) -> str:
        actions = self.context.action_plan.get("actions", [])
        actions_str = "\n".join(
            f"  {i+1}. {a.get('action', '')} (rationale: {a.get('rationale', '')})"
            for i, a in enumerate(actions)
        )
        profile = self.context.extracted_data.get("profile", {})

        return f"""Persona: {profile.get('name', 'User')}, {profile.get('job', '')}

Chosen scenario: "{self.context.scenario.get('title', '')}"
Scenario summary: {self.context.scenario.get('summary', '')}

Actions to schedule:
{actions_str}

Profile scores:
- ADHD indicator: {self._scores.adhd_indicator}
- Execution score: {self._scores.execution}
- Financial stress: {self._scores.financial_stress}

Scheduling rules based on profile:
- ADHD indicator > 0.7: Use 3h morning hyperfocus blocks for creative/deep work, 25min pomodoros for admin tasks, 10min transition buffers between context switches
- Execution score < 0.5: Prioritize actions that produce immediate tangible outputs
- Financial stress > 0.6: Front-load revenue-generating tasks in the week

Generate a weekly calendar plan with specific events. Return JSON:
{{
  "events": [
    {{
      "title": "event title",
      "description": "what to do and why",
      "start_time": "Monday 9:00 AM",
      "end_time": "Monday 12:00 PM",
      "event_type": "focus_block|admin|body_doubling|learning|break|review",
      "adhd_note": "optional ADHD accommodation note",
      "linked_action_index": 0
    }}
  ],
  "weekly_rhythm_summary": "overview of the weekly structure",
  "adhd_accommodations": ["list of ADHD-specific accommodations used"],
  "quest_connection": "how this calendar supports the chosen scenario"
}}"""

    async def plan(self) -> dict:
        return await self._llm_json(
            system=(
                "You are an ADHD-aware calendar coach. You create weekly schedules "
                "optimized for neurodivergent users based on their behavioral profile "
                "scores. Return ONLY valid JSON."
            ),
            user=self._build_prompt(),
        )

    async def execute(self, plan: dict) -> dict:
        events = plan.get("events", [])
        execution_results = []
        for event in events:
            result = await execute_action(
                "GOOGLECALENDAR_CREATE_EVENT",
                entity_id=None,
                arguments={
                    "summary": event.get("title", ""),
                    "description": event.get("description", ""),
                    "start": event.get("start_time", ""),
                    "end": event.get("end_time", ""),
                },
            )
            execution_results.append(result)
        plan["execution_results"] = execution_results
        return plan

    def to_output(self, plan: dict) -> CalendarPlan:
        return CalendarPlan(**{k: v for k, v in plan.items() if k != "execution_results"})
