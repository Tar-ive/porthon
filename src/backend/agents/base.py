"""BaseAgent ABC — plan → execute → verify lifecycle."""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import TypeVar

from openai import AsyncOpenAI

from agents.models import QuestContext

logger = logging.getLogger(__name__)
T = TypeVar("T")


class BaseAgent(ABC):
    """Abstract base for all deep agents.

    Each agent receives the full QuestContext and follows a three-phase lifecycle:
      1. plan()    — LLM generates a structured plan (JSON mode)
      2. execute() — optionally push to external services via Composio
      3. verify()  — check execution success
    """

    name: str = "base"
    timeout: float = 30.0

    def __init__(self, context: QuestContext) -> None:
        self.context = context
        self._client = AsyncOpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL") or None,
        )
        self._model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    async def _llm_json(self, system: str, user: str) -> dict:
        """Call LLM with JSON mode and return parsed dict."""
        response = await self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)

    @abstractmethod
    async def plan(self) -> dict:
        """Generate structured plan via LLM."""
        ...

    @abstractmethod
    async def execute(self, plan: dict) -> dict:
        """Execute the plan (Composio calls or dry-run)."""
        ...

    async def verify(self, result: dict) -> bool:
        """Verify execution succeeded. Override for custom checks."""
        return True

    async def run(self) -> dict:
        """Full lifecycle: plan → execute → verify."""
        logger.info(f"[{self.name}] Planning...")
        plan = await self.plan()
        logger.info(f"[{self.name}] Executing...")
        result = await self.execute(plan)
        logger.info(f"[{self.name}] Verifying...")
        ok = await self.verify(result)
        if not ok:
            logger.warning(f"[{self.name}] Verification failed")
        return result
