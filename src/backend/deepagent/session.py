"""Session abstractions for future multi-persona runtime support."""

from __future__ import annotations

from dataclasses import dataclass

from deepagent.loop import AlwaysOnMaster


@dataclass
class AgentSession:
    persona_id: str
    master: AlwaysOnMaster
