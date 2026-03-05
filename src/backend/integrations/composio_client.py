"""Composio SDK wrapper with graceful degradation.

Moved from agents/composio_tools.py → integrations/composio_client.py
so all deep-agent workers can share it.

Demo Mode:
    Set DEMO_MODE=true or use Authorization: Bearer sk_demo_* header.
    Returns mock responses that mimic Composio's real response format.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

logger = logging.getLogger(__name__)

_client = None
_connections: dict[str, str] = {}  # app_name -> connected_account_id
_initialized = False
_demo_mode = False


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
        logger.info(
            f"Composio initialized with connections: {list(_connections.keys())}"
        )
    except ImportError:
        logger.warning("composio-core not installed — dry-run mode")
    except Exception as e:
        logger.warning(f"Composio init failed: {e} — dry-run mode")


def set_demo_mode(enabled: bool):
    """Enable or disable demo mode."""
    global _demo_mode
    _demo_mode = enabled
    if enabled:
        logger.info("Demo mode enabled — mock Composio responses")


def is_demo_mode() -> bool:
    """Check if demo mode is enabled."""
    env_demo = os.environ.get("PORTTHON_OFFLINE_MODE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return _demo_mode or env_demo


def _demo_response(action_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Generate a mock response that mimics Composio's real response format."""
    action_lower = action_name.lower()

    demo_id = f"demo_{uuid.uuid4().hex[:8]}"

    if "calendar" in action_lower and "create" in action_lower:
        return {
            "dry_run": True,
            "demo_mode": True,
            "action": action_name,
            "params": params,
            "result": {
                "id": demo_id,
                "status": "confirmed",
                "summary": params.get("summary", "Demo Event"),
                "start": {
                    "dateTime": params.get("start", {}).get(
                        "dateTime", "2024-01-01T10:00:00Z"
                    )
                },
                "end": {
                    "dateTime": params.get("end", {}).get(
                        "dateTime", "2024-01-01T11:00:00Z"
                    )
                },
                "htmlLink": f"https://calendar.google.com/event?eid={demo_id}",
                "message": "[DEMO] Event created successfully",
            },
        }
    elif "calendar" in action_lower and "free" in action_lower:
        return {
            "dry_run": True,
            "demo_mode": True,
            "action": action_name,
            "params": params,
            "result": {
                "data": {
                    "calendars": {
                        "primary": {
                            "busy": [
                                {
                                    "start": "2024-01-01T09:00:00Z",
                                    "end": "2024-01-01T10:00:00Z",
                                },
                                {
                                    "start": "2024-01-01T14:00:00Z",
                                    "end": "2024-01-01T15:00:00Z",
                                },
                            ]
                        }
                    }
                },
                "message": "[DEMO] Free/busy query executed",
            },
        }
    elif "notion" in action_lower and "create" in action_lower:
        return {
            "dry_run": True,
            "demo_mode": True,
            "action": action_name,
            "params": params,
            "result": {
                "id": demo_id,
                "object": "page",
                "created_time": "2024-01-01T10:00:00Z",
                "last_edited_time": "2024-01-01T10:00:00Z",
                "message": "[DEMO] Page created in Notion",
            },
        }
    elif "facebook" in action_lower and "post" in action_lower:
        return {
            "dry_run": True,
            "demo_mode": True,
            "action": action_name,
            "params": params,
            "result": {
                "id": demo_id,
                "message": "Demo post published to Facebook",
                "post_id": f"fb_{demo_id}",
                "permalink_url": f"https://facebook.com/posts/{demo_id}",
            },
        }
    else:
        return {
            "dry_run": True,
            "demo_mode": True,
            "action": action_name,
            "params": params,
            "result": {
                "id": demo_id,
                "status": "completed",
                "message": f"[DEMO] {action_name} executed successfully",
            },
        }


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

    if is_demo_mode():
        return _demo_response(action_name, params)

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
        return {
            "dry_run": True,
            "action": action_name,
            "error": str(e),
            "params": params,
        }


def is_available() -> bool:
    """Check if Composio is configured and available."""
    _init()
    return _client is not None


def get_connection_id(app_name: str) -> str | None:
    """Get connected account ID for an app."""
    _init()
    return _connections.get(app_name)
