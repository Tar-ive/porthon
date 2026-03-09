
def generate_scenarios():
    """Fallback scenarios for Theo Nakamura (p05).

    Grounded in Theo's actual data patterns:
    - Freelance design income bimodal ($600 vs $2,200 invoices)
    - ADHD: hyperfocuses on creative work, avoids admin/invoicing
    - $5,840 credit card debt, minimum payments only
    - Portfolio growing organically (1K visitors from Instagram)
    - Rate raised once ($55→$85/hr), referrals starting to convert
    - Austin community is emotionally important

    Real scenario generation lives in pipeline/scenario_gen.py.
    This is the deterministic fallback when the pipeline is unavailable.
    """
    return [
        {
            "id": "freelance-full-time",
            "title": "Full-Time Freelance",
            "horizon": "2yr",
            "likelihood": "most_likely",
            "summary": (
                "Theo drops the barista shifts and goes full-time freelance within "
                "18 months. Revenue grows from $38K to $65K by raising rates to "
                "$100/hr for new clients and building a referral pipeline. The "
                "credit card debt is cleared by month 14 through a structured "
                "$500/month paydown plan funded by the rate increase."
            ),
            "tags": ["freelance", "finances", "confidence", "growth"],
            "pattern_ids": ["p-undercharging", "p-rate-raise", "p-referral-pipeline"],
        },
        {
            "id": "creative-pivot",
            "title": "Design Studio Launch",
            "horizon": "3yr",
            "likelihood": "possible",
            "summary": (
                "Theo leverages his motion design skills (School of Motion + "
                "Blender) and authentic social presence to launch a small design "
                "studio. Starts with one subcontractor, grows to three. The "
                "Instagram portfolio strategy that hit 1K visitors becomes a "
                "repeatable client acquisition channel. Austin's creative "
                "community becomes his network moat."
            ),
            "tags": ["career", "creativity", "portfolio", "austin"],
            "pattern_ids": ["p-creative-output", "p-social-growth", "p-austin-community"],
        },
        {
            "id": "balanced-creative",
            "title": "Sustainable Creative Life",
            "horizon": "5yr",
            "likelihood": "aspirational",
            "summary": (
                "Theo builds a sustainable creative practice that honors both "
                "his ADHD brain and financial stability. Debt-free by year 2, "
                "earning $80K+ by year 4 through a mix of retainer clients and "
                "portfolio projects. Develops an ADHD-friendly work system that "
                "uses hyperfocus windows for creative work and automates the "
                "admin he avoids. Stays in Austin — the community that matters."
            ),
            "tags": ["finances", "adhd", "sustainability", "identity", "austin"],
            "pattern_ids": [
                "p-adhd-management",
                "p-financial-stability",
                "p-austin-identity",
            ],
        },
    ]
