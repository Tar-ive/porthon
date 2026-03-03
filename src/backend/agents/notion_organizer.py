"""NotionOrganizer — creates workspace structure aligned to the chosen questline."""

from __future__ import annotations

from agents.base import BaseAgent
from agents.composio_tools import execute_action
from agents.models import NotionWorkspace, QuestContext


class NotionOrganizer(BaseAgent):
    name = "NotionOrganizer"

    def __init__(self, context: QuestContext) -> None:
        super().__init__(context)
        self._scores = context.profile_scores

    def _build_prompt(self) -> str:
        profile = self.context.extracted_data.get("profile", {})
        scenario = self.context.scenario
        actions = self.context.action_plan.get("actions", [])
        actions_str = "\n".join(f"  - {a.get('action', '')}" for a in actions)

        return f"""Persona: {profile.get('name', 'User')}, {profile.get('job', '')}

Chosen scenario: "{scenario.get('title', '')}"
Summary: {scenario.get('summary', '')}

Actions to support:
{actions_str}

Profile scores:
- Financial stress: {self._scores.financial_stress}
- Execution: {self._scores.execution}
- ADHD indicator: {self._scores.adhd_indicator}

Workspace rules:
- Financial stress > 0.6: Include a debt/finance tracker as the first page
- ADHD indicator > 0.7: Use simple single-page views, not complex multi-layer navigation
- Execution < 0.5: Focus on action-oriented pages (trackers, checklists) not documentation

Return JSON:
{{
  "pages": [
    {{
      "title": "page title",
      "page_type": "database|page|template",
      "parent": "parent page title or null",
      "properties": {{}},
      "content_markdown": "page content in markdown"
    }}
  ],
  "setup_summary": "overview of workspace structure",
  "quest_connection": "how this workspace supports the chosen scenario"
}}"""

    async def plan(self) -> dict:
        return await self._llm_json(
            system=(
                "You are a Notion workspace architect. You design simple, action-oriented "
                "workspace structures optimized for users with ADHD. Favor flat hierarchies "
                "and actionable views. Return ONLY valid JSON."
            ),
            user=self._build_prompt(),
        )

    async def execute(self, plan: dict) -> dict:
        pages = plan.get("pages", [])
        execution_results = []
        for page in pages:
            result = await execute_action(
                "NOTION_CREATE_PAGE",
                arguments={
                    "title": page.get("title", ""),
                    "page_type": page.get("page_type", "page"),
                    "content": page.get("content_markdown", ""),
                },
            )
            execution_results.append(result)
        plan["execution_results"] = execution_results
        return plan

    def to_output(self, plan: dict) -> NotionWorkspace:
        return NotionWorkspace(**{k: v for k, v in plan.items() if k != "execution_results"})
