"""
Prompt assembly — combines SOUL.md, USER.md, and retrieved KG context
into a single system prompt for the LLM.
"""

import os

AGENT_DIR = os.path.dirname(__file__)


def load_file(filename: str) -> str:
    path = os.path.join(AGENT_DIR, filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read().strip()
    return ""


def build_system_prompt(context: str | None = None, intent: str = "casual") -> str:
    """
    Build the full system prompt from SOUL + USER + optional KG context.
    """
    soul = load_file("SOUL.md")
    user = load_file("USER.md")
    
    parts = [soul, "\n\n---\n\n", user]
    
    if context:
        parts.append("\n\n---\n\n## What I Know (Retrieved from Memory)\n")
        parts.append(context)
        parts.append("\n\n*Use this context naturally. Don't quote it verbatim or cite sources. Just know it.*")
    
    # Intent-specific instructions
    if intent == "emotional":
        parts.append("\n\n**Right now:** They're expressing something emotional. Lead with empathy. Mirror their language. Keep it short. Don't problem-solve unless they ask.")
    elif intent == "advice":
        parts.append("\n\n**Right now:** They're asking for guidance. Give ONE concrete, actionable suggestion. Not a list. Consider their patterns and what's actually worked (or not) for them before.")
    elif intent == "factual":
        parts.append("\n\n**Right now:** They want specific information. Be precise and direct. If you have the data, give it. If not, say so honestly.")
    elif intent == "pattern":
        parts.append("\n\n**Right now:** They're asking about patterns. Name what you see clearly, connect the dots between sources, but don't overwhelm. One or two key patterns, stated plainly.")
    elif intent == "reflection":
        parts.append("\n\n**Right now:** They're reflecting on themselves. Be honest but kind. Reference specific things they've done or said. Help them see their trajectory, not just their position.")
    
    return "".join(parts)
