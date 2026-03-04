"""Composio SDK wrapper with graceful degradation.

Moved from agents/composio_tools.py → integrations/composio_client.py
so all deep-agent workers can share it.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_client = None
_connections: dict[str, str] = {}  # app_name -> connected_account_id
_initialized = False


def _init():
    global _client, _connections, _initialized
    if _initialized:
        return
    _initialized = True
    api_key = os.environ.get("COMPOSIO_API_KEY")
    if not api_key:
        logger.info("COMPOSIO_API_KEY not set — workers will run in dry-run mode")
        return
    try:
        from composio import Composio

        _client = Composio(api_key=api_key)
        entity = _client.get_entity("default")
        for conn in entity.get_connections():
            _connections[conn.appUniqueId] = conn.id
        logger.info(f"Composio initialized with connections: {list(_connections.keys())}")
    except ImportError:
        logger.warning("composio-core not installed — dry-run mode")
    except Exception as e:
        logger.warning(f"Composio init failed: {e} — dry-run mode")


async def execute_action(
    action_name: str,
    params: dict[str, Any] | None = None,
    app_name: str | None = None,
    entity_id: str = "default",
    # Legacy compat
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a Composio action. Returns result dict or dry-run stub."""
    _init()
    # Support legacy 'arguments' kwarg
    if params is None and arguments is not None:
        params = arguments
    if params is None:
        params = {}

    if _client is None:
        return {
            "dry_run": True,
            "action": action_name,
            "params": params,
            "message": "Composio not configured — action logged but not executed",
        }

    # Resolve connected account for the app
    connected_account = None
    if app_name and app_name in _connections:
        connected_account = _connections[app_name]
    elif not app_name:
        # Infer app from action name prefix (e.g. GOOGLECALENDAR_CREATE_EVENT -> googlecalendar)
        for known_app, acct_id in _connections.items():
            if action_name.lower().startswith(known_app.replace(" ", "")):
                connected_account = acct_id
                break

    try:
        from composio import Action

        action_enum = Action(action_name)
        result = _client.actions.execute(
            action=action_enum,
            params=params,
            entity_id=entity_id,
            connected_account=connected_account,
        )
        return {"dry_run": False, "action": action_name, "result": result}
    except Exception as e:
        logger.error(f"Composio action {action_name} failed: {e}")
        return {"dry_run": True, "action": action_name, "error": str(e), "params": params}


def is_available() -> bool:
    """Check if Composio is configured and available."""
    _init()
    return _client is not None


def get_connection_id(app_name: str) -> str | None:
    """Get connected account ID for an app."""
    _init()
    return _connections.get(app_name)
