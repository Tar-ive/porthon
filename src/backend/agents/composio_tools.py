"""Composio SDK wrapper with graceful degradation."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_composio = None
_initialized = False


def _init():
    global _composio, _initialized
    if _initialized:
        return
    _initialized = True
    api_key = os.environ.get("COMPOSIO_API_KEY")
    if not api_key:
        logger.info("COMPOSIO_API_KEY not set — agents will run in dry-run mode")
        return
    try:
        from composio import Composio
        _composio = Composio(api_key=api_key)
        logger.info("Composio client initialized")
    except ImportError:
        logger.warning("composio-core not installed — dry-run mode")
    except Exception as e:
        logger.warning(f"Composio init failed: {e} — dry-run mode")


async def execute_action(
    action: str,
    entity_id: str | None = None,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a Composio action. Returns result dict or dry-run stub."""
    _init()
    if _composio is None:
        return {
            "dry_run": True,
            "action": action,
            "arguments": arguments or {},
            "message": "Composio not configured — action logged but not executed",
        }
    try:
        result = _composio.tools.execute(
            action,
            user_id=entity_id or "default",
            arguments=arguments or {},
        )
        return {"dry_run": False, "action": action, "result": result}
    except Exception as e:
        logger.error(f"Composio action {action} failed: {e}")
        return {"dry_run": True, "action": action, "error": str(e)}


def is_available() -> bool:
    """Check if Composio is configured and available."""
    _init()
    return _composio is not None
