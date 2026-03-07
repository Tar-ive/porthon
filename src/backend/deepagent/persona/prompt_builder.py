"""Prompt assembly — combines SOUL.md, USER.md, and KG context.

Moved from agent/prompt_builder.py → deepagent/persona/prompt_builder.py.
Now reads persona files from this directory (deepagent/persona/).

Used by:
  - /api/chat endpoint (via routes_chat.py)
  - Workers that need persona-aware LLM prompts (via base worker)
"""

import os

_PERSONA_DIR = os.path.dirname(__file__)


def load_persona_file(filename: str) -> str:
    """Load a persona file (SOUL.md, USER.md) from the persona directory."""
    path = os.path.join(_PERSONA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read().strip()
    return ""


def build_system_prompt(
    context: str | None = None,
    intent: str = "casual",
    scenario: str | None = None,
) -> str:
    """Build the full system prompt from SOUL + USER + optional KG context.

    Parameters
    ----------
    context : str | None
        Retrieved KG snippets to inject as memory context.
    intent : str
        Classified intent (factual, pattern, advice, reflection, emotional, casual).
    scenario : str | None
        Active scenario description to ground the response.
    """
    soul = load_persona_file("SOUL.md")
    user = load_persona_file("USER.md")

    parts = [soul, "\n\n---\n\n", user]

    if context:
        parts.append("\n\n---\n\n## What I Know (Retrieved from Memory)\n")
        parts.append(context)
        parts.append(
            "\n\n*Use this context naturally. Don't quote it verbatim "
            "or cite sources. Just know it.*"
        )

    if scenario:
        parts.append("\n\n---\n\n## Active Scenario\n")
        parts.append(scenario)
        parts.append(
            "\n\n*Ground your responses in this scenario. When the user asks "
            "about their future, actions, or trajectory, refer to this "
            "scenario naturally.*"
        )

    _INTENT_INSTRUCTIONS = {
        "emotional": (
            "\n\n**Right now:** They're expressing something emotional. "
            "Lead with empathy. Mirror their language. Keep it short. "
            "Don't problem-solve unless they ask."
        ),
        "advice": (
            "\n\n**Right now:** They're asking for guidance. Give ONE "
            "concrete, actionable suggestion. Not a list. Consider their "
            "patterns and what's actually worked (or not) for them before."
        ),
        "factual": (
            "\n\n**Right now:** They want specific information. Be precise "
            "and direct. If you have the data, give it. If not, say so honestly."
        ),
        "pattern": (
            "\n\n**Right now:** They're asking about patterns. Name what you "
            "see clearly, connect the dots between sources, but don't "
            "overwhelm. One or two key patterns, stated plainly."
        ),
        "reflection": (
            "\n\n**Right now:** They're reflecting on themselves. Be honest "
            "but kind. Reference specific things they've done or said. Help "
            "them see their trajectory, not just their position."
        ),
    }

    instruction = _INTENT_INSTRUCTIONS.get(intent)
    if instruction:
        parts.append(instruction)

    return "".join(parts)
