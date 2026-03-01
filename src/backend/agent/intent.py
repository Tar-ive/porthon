"""
Intent classification for routing queries to the right retrieval strategy.
Keyword-based for speed. Can upgrade to LLM-based later.
"""

FACTUAL_TRIGGERS = [
    "how much", "what did i spend", "last month", "how many", "when did",
    "total", "subscription", "revenue", "income", "expense", "payment",
    "transaction", "invoice", "client", "calendar", "event", "email",
    "how often", "amount", "cost", "price", "debt",
]

PATTERN_TRIGGERS = [
    "pattern", "notice", "trend", "always", "keep doing", "habit",
    "recurring", "usually", "tendency", "behavior", "consistent",
    "over time", "changed", "getting better", "getting worse",
]

ADVICE_TRIGGERS = [
    "should i", "what do you think", "is it worth", "would you",
    "recommend", "advice", "suggest", "help me decide", "what if",
    "how do i", "strategy", "plan", "approach",
]

REFLECTION_TRIGGERS = [
    "who am i", "how am i doing", "progress", "growth", "my strengths",
    "my weaknesses", "self", "identity", "goals", "where do i stand",
    "am i", "tell me about myself",
]

EMOTIONAL_TRIGGERS = [
    "overwhelmed", "stressed", "anxious", "scared", "frustrated",
    "exhausted", "burned out", "sad", "worried", "freaking out",
    "can't do this", "give up", "stuck", "lost", "confused",
    "happy", "excited", "proud", "grateful",
]


def classify_intent(query: str) -> str:
    """
    Classify user message intent for retrieval routing.

    Returns one of: factual, pattern, advice, reflection, emotional, casual
    """
    q = query.lower().strip()

    if any(t in q for t in EMOTIONAL_TRIGGERS):
        return "emotional"
    if any(t in q for t in ADVICE_TRIGGERS):
        return "advice"
    if any(t in q for t in REFLECTION_TRIGGERS):
        return "reflection"
    if any(t in q for t in PATTERN_TRIGGERS):
        return "pattern"
    if any(t in q for t in FACTUAL_TRIGGERS):
        return "factual"

    return "casual"


# Map intent → LightRAG query mode
INTENT_TO_MODE = {
    "factual": "mix",
    "pattern": "global",
    "advice": "hybrid",
    "reflection": "hybrid",
    "emotional": None,
    "casual": None,
}
