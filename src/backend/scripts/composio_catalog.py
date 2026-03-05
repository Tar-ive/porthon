"""Composio catalog inspection for installed SDK surface.

Usage:
  COMPOSIO_CACHE_DIR=/tmp/composio_cache uv run python scripts/composio_catalog.py figma
  COMPOSIO_CACHE_DIR=/tmp/composio_cache uv run python scripts/composio_catalog.py figma --export /tmp/figma_tools.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from composio import Composio


def _dump_model(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return obj
    return {"value": str(obj)}


def inspect_toolkit(toolkit_slug: str) -> dict[str, Any]:
    composio = Composio()

    app = composio.apps.get(toolkit_slug)
    app_data = _dump_model(app)

    actions = composio.actions.get(apps=[toolkit_slug], allow_all=True)
    action_data = [_dump_model(a) for a in actions] if isinstance(actions, list) else [_dump_model(actions)]

    triggers = composio.triggers.get(apps=[toolkit_slug])
    trigger_data = [_dump_model(t) for t in triggers] if isinstance(triggers, list) else [_dump_model(triggers)]

    return {
        "toolkit": toolkit_slug,
        "app": app_data,
        "actions": action_data,
        "triggers": trigger_data,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Composio toolkit actions/triggers")
    parser.add_argument("toolkit", help="Toolkit slug (e.g. figma, notion, googlecalendar, facebook)")
    parser.add_argument("--export", help="Output JSON file path", default="")
    args = parser.parse_args()

    payload = inspect_toolkit(args.toolkit)

    print(f"Toolkit: {payload['toolkit']}")
    print(f"Actions: {len(payload.get('actions', []))}")
    print(f"Triggers: {len(payload.get('triggers', []))}")

    for action in payload.get("actions", [])[:12]:
        name = action.get("name", "")
        description = action.get("description", "")
        print(f"- {name}: {description[:100]}")

    if args.export:
        output_path = Path(args.export)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Exported catalog to {output_path}")


if __name__ == "__main__":
    main()
