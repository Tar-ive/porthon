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
import os
import time

from deepagent.workers.base import BaseWorker, WorkerExecution
from deepagent.workers.llm_schemas import (
    FacebookCommentReplyLLM,
    FacebookDraftPlanLLM,
)
from integrations.composio_client import execute_action

logger = logging.getLogger(__name__)


class FacebookWorker(BaseWorker):
    worker_id = "facebook_worker"
    label = "Facebook Publisher"

    ACTIONS = {
        "draft_posts": "_draft_posts",
        "publish_post": "_publish_post",
        "schedule_post": "_schedule_post",
        "draft_post": "_draft_posts",
        "fetch_comments": "_fetch_comments",
        "draft_comment_reply": "_draft_comment_reply",
        "reply_comment": "_reply_comment",
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

    def _normalize_comments(self, comments: list[dict]) -> list[dict]:
        normalized: list[dict] = []
        for c in comments:
            if not isinstance(c, dict):
                continue
            comment_id = str(c.get("comment_id") or c.get("id") or "").strip()
            message = str(c.get("message", "")).strip()
            if not comment_id or not message:
                continue
            normalized.append(
                {
                    "comment_id": comment_id,
                    "post_id": str(c.get("post_id", "")),
                    "message": message,
                    "from": c.get("from", {}) if isinstance(c.get("from", {}), dict) else {},
                    "created_time": c.get("created_time"),
                }
            )
        return normalized

    async def _fetch_comments(self, payload: dict) -> WorkerExecution:
        """Fetch page posts and associated comments for watch workflows."""
        if isinstance(payload.get("comments"), list):
            comments = self._normalize_comments(payload.get("comments", []))
            return WorkerExecution(
                ok=True,
                message=f"Fetched {len(comments)} seeded comments",
                data={"comments": comments},
            )

        if isinstance(payload.get("demo_comments"), list):
            comments = self._normalize_comments(payload.get("demo_comments", []))
            return WorkerExecution(
                ok=True,
                message=f"Fetched {len(comments)} demo comments",
                data={"comments": comments},
            )

        if payload.get("demo_mode") or os.environ.get("PORTTHON_OFFLINE_MODE") == "1":
            return WorkerExecution(
                ok=True,
                message="Fetched 0 demo comments",
                data={"comments": []},
            )

        page_id = payload.get("page_id", "me")
        fields = payload.get(
            "post_fields",
            "id,message,created_time",
        )
        limit_posts = int(payload.get("limit_posts", 5))
        limit_comments = int(payload.get("limit_comments", 20))

        posts_result = await execute_action(
            "FACEBOOK_GET_PAGE_POSTS",
            params={"page_id": page_id, "limit": limit_posts, "fields": fields},
            app_name="facebook",
        )
        if posts_result.get("error"):
            return WorkerExecution(ok=False, message=str(posts_result["error"]), data=posts_result)

        posts_data = posts_result.get("result", {}).get("data", {})
        posts = posts_data.get("data", []) if isinstance(posts_data, dict) else []
        post_ids_filter = set(payload.get("post_ids", []))

        comments_out: list[dict] = []
        for post in posts:
            post_id = post.get("id")
            if not post_id:
                continue
            if post_ids_filter and post_id not in post_ids_filter:
                continue
            comments_result = await execute_action(
                "FACEBOOK_GET_COMMENTS",
                params={
                    "object_id": post_id,
                    "limit": limit_comments,
                    "order": "reverse_chronological",
                    "fields": "id,message,created_time,from,parent",
                },
                app_name="facebook",
            )
            comments_data = comments_result.get("result", {}).get("data", {})
            comments = comments_data.get("data", []) if isinstance(comments_data, dict) else []
            for c in comments:
                comments_out.append(
                    {
                        "comment_id": c.get("id"),
                        "post_id": post_id,
                        "message": c.get("message", ""),
                        "from": c.get("from", {}),
                        "created_time": c.get("created_time"),
                    }
                )

        return WorkerExecution(
            ok=True,
            message=f"Fetched {len(comments_out)} comments",
            data={"comments": comments_out},
        )

    async def _draft_comment_reply(self, payload: dict) -> WorkerExecution:
        """Draft a reply for an inbound comment. No posting side effects."""
        comment_text = payload.get("comment_text", "").strip()
        scenario_title = payload.get("scenario_title", "")
        if not comment_text:
            return WorkerExecution(ok=False, message="comment_text required")

        fallback = (
            "Thanks for the comment, appreciate you being here. "
            "I’m sharing progress tied to real milestones and will post an update soon."
        )
        if scenario_title:
            fallback = (
                f"Thanks for the comment. I’m currently focused on '{scenario_title}' "
                "and will share a milestone update shortly."
            )

        if payload.get("demo_mode") or os.environ.get("PORTTHON_OFFLINE_MODE") == "1":
            return WorkerExecution(
                ok=True,
                message="Draft reply generated (demo)",
                data={"reply_text": fallback},
            )

        if not os.environ.get("OPENAI_API_KEY"):
            return WorkerExecution(
                ok=True,
                message="Draft reply generated (fallback)",
                data={"reply_text": fallback},
            )

        try:
            result = await self._llm_typed(
                system=(
                    "You draft concise, authentic Facebook replies for a creator. "
                    "Reply in one short paragraph. Return JSON with key 'reply_text'."
                ),
                user=(
                    f"Scenario: {scenario_title}\n"
                    f"Incoming comment: {comment_text}\n"
                    "Write a warm, human reply that references real progress."
                ),
                schema=FacebookCommentReplyLLM,
            )
            reply = result.reply_text or fallback
        except Exception:
            reply = fallback

        return WorkerExecution(
            ok=True,
            message="Draft reply generated",
            data={"reply_text": reply},
        )

    async def _reply_comment(self, payload: dict) -> WorkerExecution:
        """Post a reply to a comment. Approval should gate this action."""
        if payload.get("demo_mode") or os.environ.get("PORTTHON_OFFLINE_MODE") == "1":
            return WorkerExecution(
                ok=True,
                message="Comment reply logged (demo)",
                data={"demo_mode": True, "comment_id": payload.get("comment_id")},
            )

        object_id = payload.get("object_id") or payload.get("comment_id")
        message = payload.get("message", "")
        if not object_id or not message:
            return WorkerExecution(ok=False, message="comment_id/object_id and message required")

        result = await execute_action(
            "FACEBOOK_CREATE_COMMENT",
            params={"object_id": object_id, "message": message},
            app_name="facebook",
        )
        return WorkerExecution(
            ok=not result.get("dry_run", True),
            message="Comment reply posted" if not result.get("dry_run") else "Comment reply logged (dry run)",
            data=result,
        )

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
        if payload.get("demo_mode") or os.environ.get("PORTTHON_OFFLINE_MODE") == "1":
            plan = {
                "posts": [
                    {
                        "platform": "facebook",
                        "content": (
                            "This week I’m focusing on conversion-first freelance systems: "
                            "one pricing follow-up, one onboarding slot, one debt check-in."
                        ),
                        "scheduled_unix": 1773180000,
                        "post_type": "learning_in_public",
                        "hashtags": ["freelance", "design", "buildinpublic"],
                        "linked_milestone": "Pricing follow-up sent",
                    },
                    {
                        "platform": "facebook",
                        "content": (
                            "Small win: I moved a portfolio deliverable from draft to shipped "
                            "and tied it to a real client pipeline milestone."
                        ),
                        "scheduled_unix": 1773439200,
                        "post_type": "portfolio_piece",
                        "hashtags": ["portfolio", "creativework", "austin"],
                        "linked_milestone": "Portfolio challenge shipped",
                    },
                ],
                "posting_cadence": "2x per week",
                "brand_voice_notes": "Grounded, transparent, milestone-linked updates.",
                "quest_connection": "Posts bridge narrative to measurable execution.",
            }
            return WorkerExecution(
                ok=True,
                message="Drafted 2 deterministic demo posts (not published)",
                data=plan,
            )

        kg_context = payload.get("kg_context", {})

        recent_posts = await self._fetch_recent_posts()
        logger.info("Facebook: found %d recent posts for voice calibration", len(recent_posts))

        prompt = self._build_content_prompt(recent_posts, kg_context, payload)
        plan_model = await self._llm_typed(
            system=(
                "You are a personal brand content strategist. Create authentic content "
                "that bridges public and private personas. Use unix timestamps. "
                "Return ONLY valid JSON."
            ),
            user=prompt,
            schema=FacebookDraftPlanLLM,
        )
        plan = plan_model.model_dump(mode="json")

        logger.info("Facebook: drafted %d posts", len(plan_model.posts))

        return WorkerExecution(
            ok=True, message=f"Drafted {len(plan_model.posts)} posts (not published)", data=plan
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
