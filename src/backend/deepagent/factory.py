"""Factory helpers for deep-agent services."""

from __future__ import annotations

from pathlib import Path

from deepagent.loop import AlwaysOnMaster


def create_master(state_path: Path, tick_seconds: int = 900) -> AlwaysOnMaster:
    return AlwaysOnMaster(state_path=state_path, tick_seconds=tick_seconds)
