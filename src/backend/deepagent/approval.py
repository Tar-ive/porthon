"""Approval policy helpers for high-impact actions."""

from __future__ import annotations

from deepagent.policy import requires_approval as _requires_approval


def requires_approval(worker_id: str, action: str) -> bool:
    return _requires_approval(worker_id, action)
