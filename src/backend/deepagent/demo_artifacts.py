"""Deterministic demo artifacts and workflow helpers for sk_demo_* mode."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any


def build_proactive_artifacts(scenario: dict[str, Any]) -> dict[str, Any]:
    scenario_title = scenario.get("title", "Questline")
    return {
        "calendar": {
            "events": [
                {
                    "title": "Deep Work: Portfolio Sprint (UT Library)",
                    "type": "focus_block",
                    "duration_minutes": 180,
                    "location": "UT Library",
                },
                {
                    "title": "Deep Work: Client Deliverable Block (UT Library)",
                    "type": "focus_block",
                    "duration_minutes": 180,
                    "location": "UT Library",
                },
                {
                    "title": "Admin Sprint: Invoice Follow-up",
                    "type": "admin",
                    "duration_minutes": 45,
                    "location": "Home Desk",
                },
                {
                    "title": "Debt-Paydown Review",
                    "type": "review",
                    "duration_minutes": 30,
                    "location": "Home Desk",
                },
            ],
        },
        "notion_leads": {
            "database_title": "Leads",
            "data_source_title": "Theo Leads",
            "leads": [
                {
                    "name": "Referral Lead",
                    "source": "Referral",
                    "lead_type": "Referral",
                    "status": "Lead",
                    "priority": "High",
                    "deal_size": 1500,
                    "next_action": "Send intro scope and availability",
                    "next_follow_up_date": "2026-03-09",
                },
                {
                    "name": "Portfolio Lead",
                    "source": "Portfolio",
                    "lead_type": "Inbound",
                    "status": "Proposal sent",
                    "priority": "High",
                    "deal_size": 2500,
                    "next_action": "Follow up on proposal feedback",
                    "next_follow_up_date": "2026-03-10",
                },
                {
                    "name": "Direct Lead",
                    "source": "Direct",
                    "lead_type": "Outbound",
                    "status": "Contacted",
                    "priority": "Medium",
                    "deal_size": 3000,
                    "next_action": "Book discovery call",
                    "next_follow_up_date": "2026-03-11",
                },
            ],
        },
        "notion_opportunity": {
            "workspace_title": f"Questline: {scenario_title}",
            "progress_page": "Progress: Next Actions",
        },
        "figma": {
            "challenge_briefs": [
                "Challenge 1: Conversion-first landing refresh for a local service brand",
                "Challenge 2: Brand motion system for an Austin creator collective",
                "Challenge 3: Portfolio case-study narrative sprint with measurable KPI",
            ],
            "weekly_milestones": [
                "Week 1: Brief + concept frames",
                "Week 2: Mid-fidelity exploration",
                "Week 3: Final polish + share-out",
            ],
        },
        "kg_context": {
            "signals": [
                "public/private delta",
                "learning-vs-conversion mismatch",
                "financial stress triangulation",
                "ADHD execution constraints",
            ]
        },
        "integration_links": {
            "calendar": [],
            "notion": [],
            "figma": [],
        },
    }


def build_facebook_watch_state(payload: dict[str, Any]) -> dict[str, Any]:
    demo_comments = payload.get("demo_comments", []) or []
    normalized_demo_comments: list[dict[str, Any]] = []
    for c in demo_comments:
        if not isinstance(c, dict):
            continue
        comment_id = str(c.get("comment_id", "")).strip()
        message = str(c.get("message", "")).strip()
        if not comment_id or not message:
            continue
        normalized_demo_comments.append(
            {
                "comment_id": comment_id,
                "post_id": str(c.get("post_id", "")),
                "message": message,
                "from": c.get("from", {}) if isinstance(c.get("from", {}), dict) else {},
                "created_time": c.get("created_time"),
            }
        )

    return {
        "page_id": payload.get("page_id", "me"),
        "post_ids": payload.get("post_ids", []),
        "limit_posts": int(payload.get("limit_posts", 5)),
        "limit_comments": int(payload.get("limit_comments", 20)),
        "demo_mode": bool(payload.get("demo_mode", True)),
        "demo_comments": normalized_demo_comments,
        "seen_comment_ids": payload.get("seen_comment_ids", []),
        "started_at": _now_iso(),
        "last_polled_at": None,
    }


def build_figma_watch_state(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "enabled": True,
        "team_id": str(payload.get("team_id", "")),
        "file_key": str(payload.get("file_key", "")),
        "demo_mode": bool(payload.get("demo_mode", True)),
        "seen_event_ids": payload.get("seen_event_ids", []),
        "started_at": _now_iso(),
        "last_event_at": None,
    }


def make_draft_reply(comment_text: str, scenario_title: str = "") -> str:
    """Create a deterministic fallback reply when LLM is unavailable."""
    base = "Thanks for the comment, really appreciate you following this."
    if scenario_title:
        base += f" I’m currently focused on '{scenario_title}' and sharing progress transparently."
    if comment_text:
        base += " I’ll post an update tied to a measurable milestone shortly."
    return base


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
