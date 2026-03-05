"""Execution policy for worker actions."""

from __future__ import annotations

from typing import Literal

ActionRisk = Literal["read", "write_reversible", "write_irreversible"]

IRREVERSIBLE_ACTIONS: dict[str, set[str]] = {
    "facebook_worker": {"publish_post", "schedule_post", "reply_comment"},
    "calendar_worker": {"reschedule_week", "delete_block"},
}

WRITE_ACTION_PREFIXES: dict[str, tuple[str, ...]] = {
    "calendar_worker": ("create_", "move_", "sync_"),
    "notion_leads_worker": ("create_", "add_", "sync_", "upsert_", "patch_"),
    "notion_opportunity_worker": ("create_", "add_", "sync_"),
    "facebook_worker": ("draft_", "publish_", "schedule_", "reply_"),
    "figma_worker": ("generate_", "comment_", "process_"),
}


def classify_action_risk(worker_id: str, action: str) -> ActionRisk:
    if action in IRREVERSIBLE_ACTIONS.get(worker_id, set()):
        return "write_irreversible"

    prefixes = WRITE_ACTION_PREFIXES.get(worker_id, ())
    if action.startswith(prefixes):
        return "write_reversible"

    return "read"


def is_irreversible_action(worker_id: str, action: str) -> bool:
    return classify_action_risk(worker_id, action) == "write_irreversible"


def requires_approval(worker_id: str, action: str) -> bool:
    return is_irreversible_action(worker_id, action)
