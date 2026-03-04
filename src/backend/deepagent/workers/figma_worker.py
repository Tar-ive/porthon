"""Figma Plan Generator Worker — design challenges + learning paths.

Absorbs agents/figma_learning.py:
  - Figma connection verification via Composio
  - Design challenge generation calibrated to skill level
  - Portfolio-worthy project scaffolding

Composio actions:
  FIGMA_GET_CURRENT_USER       — verify connection
  FIGMA_GET_FILE_JSON          — analyze existing files
  FIGMA_EXTRACT_DESIGN_TOKENS  — extract color/typography
"""

from __future__ import annotations

import logging

from deepagent.workers.base import BaseWorker, WorkerExecution
from integrations.composio_client import execute_action

logger = logging.getLogger(__name__)


class FigmaWorker(BaseWorker):
    worker_id = "figma_worker"
    label = "Figma Plan Generator"

    ACTIONS = {
        "generate_challenge": "_generate_challenge",
        "verify_connection": "_verify_connection",
    }

    async def execute(self, action: str, payload: dict) -> WorkerExecution:
        handler_name = self.ACTIONS.get(action)
        if not handler_name:
            return WorkerExecution(ok=False, message=f"Unknown action: {action}")
        handler = getattr(self, handler_name)
        return await handler(payload)

    async def _fetch_figma_context(self) -> dict:
        """Pull Figma context: user info + file analysis if available."""
        ctx: dict = {}

        user_result = await execute_action(
            "FIGMA_GET_CURRENT_USER", params={}, app_name="figma",
        )
        if not user_result.get("dry_run"):
            data = user_result.get("result", {}).get("data", {})
            ctx["figma_user"] = {
                "handle": data.get("handle"),
                "email": data.get("email"),
            }
            logger.info("Figma: connected as %s", data.get("handle"))

        return ctx

    def _build_challenge_prompt(self, figma_ctx: dict, kg_context: dict, payload: dict) -> str:
        """Build a design challenge prompt using KG context."""
        kg_snippets = kg_context.get("snippets", [])
        kg_text = "\n".join(f"  - {s}" for s in kg_snippets[:5]) if kg_snippets else "  (no KG context)"

        figma_info = ""
        if figma_ctx.get("figma_user"):
            figma_info = f"\nFigma account: {figma_ctx['figma_user'].get('handle')} (connected)"

        return f"""Persona context from knowledge graph:
{kg_text}

Chosen scenario: "{payload.get('scenario_title', '')}"
{figma_info}

Design challenge rules:
- Challenges must produce portfolio-worthy artifacts, not just exercises
- Simulate real client work (Austin-based clients, motion design, brand identity)
- Calibrate difficulty to intermediate level
- Each challenge should build toward the scenario goal
- Keep individual tasks scoped to 4 hours max

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
  "portfolio_targets": ["target1"],
  "quest_connection": "how this supports the scenario"
}}"""

    async def _generate_challenge(self, payload: dict) -> WorkerExecution:
        """Generate design challenges calibrated to KG context."""
        kg_context = payload.get("kg_context", {})

        figma_ctx = await self._fetch_figma_context()

        prompt = self._build_challenge_prompt(figma_ctx, kg_context, payload)
        plan = await self._llm_json(
            system=(
                "You are a design learning coach. Create structured design challenges "
                "that produce portfolio-worthy work. Return ONLY valid JSON."
            ),
            user=prompt,
        )

        logger.info(
            "Figma: generated %d challenges, %d milestones",
            len(plan.get("challenges", [])),
            len(plan.get("milestones", [])),
        )

        return WorkerExecution(
            ok=True,
            message=f"Generated {len(plan.get('challenges', []))} design challenges",
            data=plan,
        )

    async def _verify_connection(self, payload: dict) -> WorkerExecution:
        """Verify the Figma Composio connection is alive."""
        ctx = await self._fetch_figma_context()
        connected = bool(ctx.get("figma_user"))
        return WorkerExecution(
            ok=connected,
            message="Figma connected" if connected else "Figma not connected",
            data=ctx,
        )
