"""Figma Plan Generator Worker — direct Figma API + collaboration workflows."""

from __future__ import annotations

import logging
import os

from deepagent.workers.base import BaseWorker, WorkerExecution
from deepagent.workers.llm_schemas import (
    FigmaCollabDeltaLLM,
    FigmaFollowupDraftLLM,
    FigmaPlanLLM,
)
from integrations.figma_api import FigmaApiError, get_figma_api
from integrations.figma_webhooks import normalize_figma_webhook_payload

logger = logging.getLogger(__name__)


class FigmaWorker(BaseWorker):
    worker_id = "figma_worker"
    label = "Figma Plan Generator"

    ACTIONS = {
        "generate_challenge": "_generate_challenge",
        "verify_connection": "_verify_connection",
        "generate_plan": "_generate_challenge",
        "comment_file": "_comment_file",
        "reply_comment": "_reply_comment",
        "process_webhook_event": "_process_webhook_event",
        "summarize_collab_delta": "_process_webhook_event",
    }

    async def execute(self, action: str, payload: dict) -> WorkerExecution:
        handler_name = self.ACTIONS.get(action)
        if not handler_name:
            return WorkerExecution(ok=False, message=f"Unknown action: {action}")
        handler = getattr(self, handler_name)
        return await handler(payload)

    async def _fetch_figma_context(self) -> dict:
        """Pull Figma context: current authenticated user."""
        ctx: dict = {}
        api = get_figma_api()
        if not api.is_configured():
            return ctx

        try:
            user = await api.get_me()
        except Exception:  # noqa: BLE001
            return ctx

        handle = user.get("handle") or user.get("email") or user.get("id")
        ctx["figma_user"] = {
            "id": user.get("id"),
            "handle": handle,
            "email": user.get("email"),
        }
        logger.info("Figma: connected as %s", handle)

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
        if payload.get("demo_mode") or os.environ.get("PORTTHON_OFFLINE_MODE") == "1":
            plan = {
                "challenges": [
                    {
                        "title": "Conversion-first landing refresh",
                        "brief": "Rework a local service landing page to improve inquiry conversion.",
                        "skill_focus": ["layout", "copy hierarchy", "CTA clarity"],
                        "difficulty": "intermediate",
                        "estimated_hours": 4.0,
                        "portfolio_worthy": True,
                    },
                    {
                        "title": "Austin creative brand motion kit",
                        "brief": "Build a lightweight motion system for a creator collective.",
                        "skill_focus": ["motion", "component systems"],
                        "difficulty": "intermediate",
                        "estimated_hours": 4.0,
                        "portfolio_worthy": True,
                    },
                    {
                        "title": "Case-study narrative sprint",
                        "brief": "Turn one shipped piece into a KPI-anchored case study.",
                        "skill_focus": ["storytelling", "visual sequencing"],
                        "difficulty": "intermediate",
                        "estimated_hours": 4.0,
                        "portfolio_worthy": True,
                    },
                ],
                "milestones": [
                    {"title": "Week 1", "target_date": "Week 1", "deliverable": "Brief + concepts", "linked_challenge": "Conversion-first landing refresh"},
                    {"title": "Week 2", "target_date": "Week 2", "deliverable": "Mid-fidelity exploration", "linked_challenge": "Austin creative brand motion kit"},
                    {"title": "Week 3", "target_date": "Week 3", "deliverable": "Final polish + recap", "linked_challenge": "Case-study narrative sprint"},
                ],
                "weekly_practice_hours": 6.0,
                "portfolio_targets": ["3 portfolio-ready briefs completed"],
                "quest_connection": "Challenges directly support scenario execution and visibility.",
            }
            return WorkerExecution(
                ok=True,
                message="Generated 3 deterministic demo challenges",
                data=plan,
            )

        kg_context = payload.get("kg_context", {})

        figma_ctx = await self._fetch_figma_context()

        prompt = self._build_challenge_prompt(figma_ctx, kg_context, payload)
        plan_model = await self._llm_typed(
            system=(
                "You are a design learning coach. Create structured design challenges "
                "that produce portfolio-worthy work. Return ONLY valid JSON."
            ),
            user=prompt,
            schema=FigmaPlanLLM,
        )
        plan = plan_model.model_dump(mode="json")

        logger.info(
            "Figma: generated %d challenges, %d milestones",
            len(plan_model.challenges),
            len(plan_model.milestones),
        )

        return WorkerExecution(
            ok=True,
            message=f"Generated {len(plan_model.challenges)} design challenges",
            data=plan,
        )

    async def _verify_connection(self, payload: dict) -> WorkerExecution:
        """Verify the direct Figma connection is alive."""
        ctx = await self._fetch_figma_context()
        connected = bool(ctx.get("figma_user"))
        return WorkerExecution(
            ok=connected,
            message="Figma connected" if connected else "Figma not connected",
            data=ctx,
        )

    async def _comment_file(self, payload: dict) -> WorkerExecution:
        """Add a root comment on a Figma file."""
        if payload.get("demo_mode") or os.environ.get("PORTTHON_OFFLINE_MODE") == "1":
            file_key = payload.get("file_key", "")
            message = payload.get("message", "")
            if not file_key or not message:
                return WorkerExecution(ok=False, message="file_key and message are required")
            return WorkerExecution(
                ok=True,
                message="Figma comment logged (demo)",
                data={
                    "demo_mode": True,
                    "file_key": file_key,
                    "message": message,
                    "external_links": {"figma_file": f"https://www.figma.com/file/{file_key}"},
                },
            )

        file_key = payload.get("file_key", "")
        message = payload.get("message", "")
        if not file_key or not message:
            return WorkerExecution(ok=False, message="file_key and message are required")

        api = get_figma_api()
        if not api.is_configured():
            return WorkerExecution(ok=False, message="FIGMA_API_KEY is not configured")

        try:
            result = await api.post_comment(file_key=file_key, message=message)
        except FigmaApiError as exc:
            return WorkerExecution(ok=False, message=f"Figma API error ({exc.status_code})")
        except Exception as exc:  # noqa: BLE001
            return WorkerExecution(ok=False, message=f"Figma API error: {exc}")

        return WorkerExecution(
            ok=True,
            message="Figma comment added",
            data={
                **result,
                "external_links": {"figma_file": f"https://www.figma.com/file/{file_key}"},
            },
        )

    async def _reply_comment(self, payload: dict) -> WorkerExecution:
        """Reply to a root comment on a Figma file."""
        file_key = str(payload.get("file_key", "")).strip()
        comment_id = str(payload.get("comment_id", "")).strip()
        message = str(payload.get("message", "")).strip()
        if not file_key or not comment_id or not message:
            return WorkerExecution(ok=False, message="file_key, comment_id, and message are required")

        if payload.get("demo_mode") or os.environ.get("PORTTHON_OFFLINE_MODE") == "1":
            return WorkerExecution(
                ok=True,
                message="Figma reply logged (demo)",
                data={
                    "comment_id": comment_id,
                    "file_key": file_key,
                    "message": message,
                    "external_links": {"figma_file": f"https://www.figma.com/file/{file_key}"},
                },
            )

        api = get_figma_api()
        if not api.is_configured():
            return WorkerExecution(ok=False, message="FIGMA_API_KEY is not configured")

        try:
            result = await api.post_comment(
                file_key=file_key,
                comment_id=comment_id,
                message=message,
            )
        except FigmaApiError as exc:
            return WorkerExecution(ok=False, message=f"Figma API error ({exc.status_code})")
        except Exception as exc:  # noqa: BLE001
            return WorkerExecution(ok=False, message=f"Figma API error: {exc}")

        return WorkerExecution(
            ok=True,
            message="Figma reply posted",
            data={
                **result,
                "comment_id": comment_id,
                "file_key": file_key,
                "message": message,
                "external_links": {"figma_file": f"https://www.figma.com/file/{file_key}"},
            },
        )

    def _extract_comment_event(self, payload: dict) -> dict:
        normalized = normalize_figma_webhook_payload(payload if isinstance(payload, dict) else {})
        return {
            "event_id": str(normalized.get("event_id", "")).strip(),
            "comment_id": str(normalized.get("comment_id", "")).strip(),
            "file_key": str(normalized.get("file_key", "")).strip(),
            "message": str(normalized.get("message", "")).strip(),
            "from": normalized.get("from", {}) if isinstance(normalized.get("from", {}), dict) else {},
        }

    async def _process_webhook_event(self, payload: dict) -> WorkerExecution:
        normalized = self._extract_comment_event(payload)
        if not normalized["comment_id"] or not normalized["message"]:
            return WorkerExecution(ok=False, message="comment_id and message are required")

        file_key = normalized["file_key"]
        file_url = f"https://www.figma.com/file/{file_key}" if file_key else ""
        fallback_summary = "New collaboration comment received and queued for focused follow-up."
        fallback_next_action = "Acknowledge the comment and propose one concrete next design action."
        fallback_comment = (
            "Thanks for the context. I captured this and will respond with one clear next step on the design."
        )

        if payload.get("demo_mode") or os.environ.get("PORTTHON_OFFLINE_MODE") == "1":
            return WorkerExecution(
                ok=True,
                message="Processed Figma collaboration event (demo)",
                data={
                    "event_id": normalized["event_id"],
                    "comment_id": normalized["comment_id"],
                    "file_key": file_key,
                    "message": normalized["message"],
                    "summary": fallback_summary,
                    "next_action": fallback_next_action,
                    "draft_reply": fallback_comment,
                    "status": "ready_to_send",
                    "external_links": {"figma_file": file_url} if file_url else {},
                },
            )

        if not os.environ.get("OPENAI_API_KEY"):
            return WorkerExecution(
                ok=True,
                message="Processed Figma collaboration event (fallback)",
                data={
                    "event_id": normalized["event_id"],
                    "comment_id": normalized["comment_id"],
                    "file_key": file_key,
                    "message": normalized["message"],
                    "summary": fallback_summary,
                    "next_action": fallback_next_action,
                    "draft_reply": fallback_comment,
                    "status": "ready_to_send",
                    "external_links": {"figma_file": file_url} if file_url else {},
                },
            )

        try:
            delta = await self._llm_typed(
                system=(
                    "You are a Figma collaboration analyst. Summarize the collaboration delta "
                    "and propose one concrete next step. Return only JSON."
                ),
                user=(
                    f"Incoming Figma comment: {normalized['message']}\n"
                    f"Scenario: {payload.get('scenario_title', '')}\n"
                    "Respond with concise, execution-focused output."
                ),
                schema=FigmaCollabDeltaLLM,
            )
            draft = await self._llm_typed(
                system=(
                    "You draft concise Figma follow-up comments for collaborative design work. "
                    "Return only JSON."
                ),
                user=(
                    f"Incoming comment: {normalized['message']}\n"
                    f"Suggested next action: {delta.next_action}\n"
                    "Draft a short collaborative follow-up comment."
                ),
                schema=FigmaFollowupDraftLLM,
            )
            summary = delta.summary
            next_action = delta.next_action
            draft_reply = draft.draft_comment
        except Exception:  # noqa: BLE001
            summary = fallback_summary
            next_action = fallback_next_action
            draft_reply = fallback_comment

        return WorkerExecution(
            ok=True,
            message="Processed Figma collaboration event",
            data={
                "event_id": normalized["event_id"],
                "comment_id": normalized["comment_id"],
                "file_key": file_key,
                "message": normalized["message"],
                "summary": summary,
                "next_action": next_action,
                "draft_reply": draft_reply,
                "status": "ready_to_send",
                "external_links": {"figma_file": file_url} if file_url else {},
            },
        )
