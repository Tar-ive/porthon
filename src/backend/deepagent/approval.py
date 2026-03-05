"""Approval policy helpers for high-impact actions."""

from __future__ import annotations

HIGH_IMPACT_ACTIONS = {
    "facebook_worker": {"publish_post", "schedule_post", "reply_comment"},
    "calendar_worker": {"reschedule_week", "delete_block"},
}


def requires_approval(worker_id: str, action: str) -> bool:
    return action in HIGH_IMPACT_ACTIONS.get(worker_id, set())
