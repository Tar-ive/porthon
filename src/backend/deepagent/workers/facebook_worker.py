"""Facebook Publisher Worker — persona-aware content scheduling.

Absorbs agents/content_creator.py:
  - Facebook post scheduling via Composio
  - Voice calibration from existing posts
  - Learning-in-public content strategy

Composio actions:
  FACEBOOK_GET_PAGE_POSTS  — fetch recent posts to calibrate voice
  FACEBOOK_CREATE_POST     — schedule posts (published=false)
"""

from __future__ import annotations

import logging
import time

from deepagent.workers.base import BaseWorker, WorkerExecution
from integrations.composio_client import execute_action

logger = logging.getLogger(__name__)


class FacebookWorker(BaseWorker):
    worker_id = "facebook_worker"
    label = "Facebook Publisher"

    ACTIONS = {
        "draft_posts": "_draft_posts",
        "publish_post": "_publish_post",
        "schedule_post": "_schedule_post",
    }

    async def execute(self, action: str, payload: dict) -> WorkerExecution:
        # Publishing actions require approval
        if action in {"publish_post", "schedule_post"}:
            return WorkerExecution(
                ok=False,
                message=f"Action '{action}' requires user approval",
                approval_required=True,
                approval_reason="Publishing or scheduling social media posts requires approval",
            )

        handler_name = self.ACTIONS.get(action)
        if not handler_name:
            return WorkerExecution(ok=False, message=f"Unknown action: {action}")
        handler = getattr(self, handler_name)
        return await handler(payload)

    async def _fetch_recent_posts(self) -> list[dict]:
        """Get existing Facebook posts to calibrate voice."""
        result = await execute_action(
            "FACEBOOK_GET_PAGE_POSTS",
            params={"page_id": "me", "limit": 5, "fields": "message,created_time"},
            app_name="facebook",
        )
        if result.get("dry_run") or result.get("error"):
            return []
        data = result.get("result", {}).get("data", {})
        posts = data.get("data", []) if isinstance(data, dict) else []
        return posts[:5]

    def _build_content_prompt(self, recent_posts: list[dict], kg_context: dict, payload: dict) -> str:
        """Build a content planning prompt using KG context."""
        kg_snippets = kg_context.get("snippets", [])
        kg_text = "\n".join(f"  - {s}" for s in kg_snippets[:5]) if kg_snippets else "  (no KG context)"

        fb_context = ""
        if recent_posts:
            fb_context = "\nRecent Facebook posts (calibrate to this voice):\n"
            fb_context += "\n".join(
                f"  - {p.get('message', '')[:100]}" for p in recent_posts[:3]
            )

        return f"""Persona context from knowledge graph:
{kg_text}

Chosen scenario: "{payload.get('scenario_title', '')}"
{fb_context}

Content rules:
- "Learning in public" posts bridging public persona with private goals
- Align content to questline milestones
- Posts demonstrate progress, not just intentions
- Use authentic voice — not corporate, not motivational poster
- Provide unix timestamps for scheduling (next 2 weeks)

Return JSON:
{{
  "posts": [
    {{
      "platform": "facebook",
      "content": "post content text",
      "scheduled_unix": 1741996800,
      "post_type": "design_tip|learning_in_public|portfolio_piece|personal_brand",
      "hashtags": ["tag1"],
      "linked_milestone": "milestone title or null"
    }}
  ],
  "posting_cadence": "e.g. 2x per week",
  "brand_voice_notes": "guidance on tone and style",
  "quest_connection": "how this content plan supports the chosen scenario"
}}"""

    async def _draft_posts(self, payload: dict) -> WorkerExecution:
        """Generate draft posts using KG context and voice calibration."""
        kg_context = payload.get("kg_context", {})

        recent_posts = await self._fetch_recent_posts()
        logger.info("Facebook: found %d recent posts for voice calibration", len(recent_posts))

        prompt = self._build_content_prompt(recent_posts, kg_context, payload)
        plan = await self._llm_json(
            system=(
                "You are a personal brand content strategist. Create authentic content "
                "that bridges public and private personas. Use unix timestamps. "
                "Return ONLY valid JSON."
            ),
            user=prompt,
        )

        logger.info("Facebook: drafted %d posts", len(plan.get("posts", [])))

        return WorkerExecution(
            ok=True,
            message=f"Drafted {len(plan.get('posts', []))} posts (not published)",
            data=plan,
        )

    async def _publish_post(self, payload: dict) -> WorkerExecution:
        """Publish a single post. Always requires approval (handled above)."""
        content = payload.get("content", "")
        if not content:
            return WorkerExecution(ok=False, message="Post content required")

        params: dict = {"message": content}
        scheduled_unix = payload.get("scheduled_unix")
        if scheduled_unix and int(scheduled_unix) > int(time.time()):
            params["published"] = False
            params["scheduled_publish_time"] = scheduled_unix

        result = await execute_action(
            "FACEBOOK_CREATE_POST",
            params=params,
            app_name="facebook",
        )

        return WorkerExecution(
            ok=not result.get("dry_run", True),
            message="Post published" if not result.get("dry_run") else "Post logged (dry run)",
            data=result,
        )

    async def _schedule_post(self, payload: dict) -> WorkerExecution:
        """Schedule a post for future publication. Always requires approval."""
        return await self._publish_post(payload)
