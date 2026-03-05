"""Base contracts and abstract worker for the deep-agent runtime.

Enriched from the original stub to include:
  - _llm_json() helper (absorbed from agents/base.py)
  - Persona context loading (reads SOUL.md/USER.md from deepagent/persona/)
  - KG context helper for workers that need personalization
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)


@dataclass
class WorkerExecution:
    """Result of a single worker action."""
    ok: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    approval_required: bool = False
    approval_reason: str = ""


class BaseWorker(ABC):
    """Abstract base for all deep-agent workers.

    Workers are the hands of the system — they execute actions in real
    tools (Calendar, Notion, Facebook, Figma) or query the knowledge
    graph. Every worker inherits shared capabilities:

      - _llm_json()      → structured LLM calls with JSON mode
      - _load_persona()   → SOUL.md + USER.md for persona-aware prompts
      - execute()         → the abstract method each worker implements
    """

    worker_id: str = "base"
    label: str = "Base Worker"

    def __init__(self) -> None:
        self._openai_client = None
        self._model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    def _get_openai_client(self):
        """Lazy-init an AsyncOpenAI client."""
        if self._openai_client is None:
            from openai import AsyncOpenAI
            self._openai_client = AsyncOpenAI(
                api_key=os.environ.get("OPENAI_API_KEY"),
                base_url=os.environ.get("OPENAI_BASE_URL") or None,
            )
        return self._openai_client

    async def _llm_json(self, system: str, user: str) -> dict:
        """Call LLM with JSON mode and return parsed dict.

        Absorbed from agents/base.py. Uses json_repair for resilience
        against malformed LLM responses.
        """
        client = self._get_openai_client()
        response = await client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
            max_tokens=4000,
        )
        raw = response.choices[0].message.content or "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("[%s] Invalid JSON from model, attempting repair", self.worker_id)
            from json_repair import repair_json
            repaired_obj = repair_json(raw, return_objects=True)
            if isinstance(repaired_obj, dict):
                return repaired_obj
            if isinstance(repaired_obj, list):
                return {"items": repaired_obj}
            raise

    async def _llm_typed(
        self,
        system: str,
        user: str,
        schema: type[TModel],
    ) -> TModel:
        """Call LLM and validate the JSON response with a strict Pydantic schema."""
        payload = await self._llm_json(system=system, user=user)
        try:
            return schema.model_validate(payload)
        except ValidationError as exc:
            logger.error(
                "[%s] LLM output failed schema %s validation: %s",
                self.worker_id,
                schema.__name__,
                exc,
            )
            raise ValueError(
                f"LLM output failed {schema.__name__} validation"
            ) from exc

    def _load_persona(self) -> tuple[str, str]:
        """Load SOUL.md and USER.md from deepagent/persona/.

        Returns (soul_text, user_text). Cached after first load.
        """
        if not hasattr(self, "_cached_persona"):
            persona_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "persona"
            )
            soul_path = os.path.join(persona_dir, "SOUL.md")
            user_path = os.path.join(persona_dir, "USER.md")

            soul = ""
            if os.path.exists(soul_path):
                with open(soul_path) as f:
                    soul = f.read().strip()

            user = ""
            if os.path.exists(user_path):
                with open(user_path) as f:
                    user = f.read().strip()

            self._cached_persona = (soul, user)

        return self._cached_persona

    @abstractmethod
    async def execute(self, action: str, payload: dict) -> WorkerExecution:
        """Execute a worker action. Must be implemented by each worker.

        Parameters
        ----------
        action : str
            The action to execute (must match a SKILL.md action).
        payload : dict
            Parameters for this action, including optional kg_context
            injected by the dispatcher.

        Returns
        -------
        WorkerExecution
            Result of the action with ok/fail status and optional data.
        """
        return WorkerExecution(ok=True, message="no-op")
