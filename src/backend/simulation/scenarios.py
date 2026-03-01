
def generate_scenarios():
    """Stub: returns dummy life scenarios for Jordan Lee (p01). Real implementation MUST match this schema for frontend compatibility."""
    return [
        {
            "id": "career-momentum",
            "title": "Career Momentum",
            "horizon": "5yr",
            "likelihood": "most_likely",
            "summary": "Jordan accelerates into a senior engineering role, doubles income, and builds a strong professional network through consistent skill investment.",
            "tags": ["career", "finance", "growth"],
            "pattern_ids": ["p-spend-edu", "p-career-velocity"],
        },
        {
            "id": "creative-pivot",
            "title": "Creative Pivot",
            "horizon": "5yr",
            "likelihood": "possible",
            "summary": "Jordan transitions toward product design and independent consulting, trading salary ceiling for autonomy and creative fulfillment.",
            "tags": ["career", "creativity", "lifestyle"],
            "pattern_ids": ["p-creative-output", "p-social-engagement"],
        },
        {
            "id": "balanced-flourishing",
            "title": "Balanced Flourishing",
            "horizon": "10yr",
            "likelihood": "aspirational",
            "summary": "Jordan achieves financial independence through disciplined saving and investment, allowing deep investment in relationships, health, and meaningful work.",
            "tags": ["finance", "health", "relationships", "purpose"],
            "pattern_ids": ["p-financial-discipline", "p-health-consistency", "p-social-depth"],
        },
    ]
