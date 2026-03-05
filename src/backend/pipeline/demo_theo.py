"""Deterministic Theo (p05) data generators for sk_demo_* mode."""

from __future__ import annotations

from typing import Any


def normalize_demo_scenario_id(scenario_id: str) -> str:
    if scenario_id.startswith("s_"):
        return f"scen_{scenario_id.removeprefix('s_')}"
    return scenario_id


def generate_demo_scenarios(persona_id: str = "p05") -> list[dict[str, Any]]:
    if persona_id != "p05":
        return []
    return [
        {
            "id": "scen_001",
            "title": "Conversion-First Freelance Stabilization",
            "horizon": "1yr",
            "likelihood": "most_likely",
            "summary": (
                "Theo shifts focus from endless learning to revenue conversion by "
                "productizing core design offers, tightening follow-up cadence, and "
                "protecting deep-work blocks."
            ),
            "tags": ["conversion", "revenue", "focus", "freelance"],
            "pattern_ids": [
                "public_private_delta",
                "learning_vs_conversion_mismatch",
                "financial_stress_triangulation",
            ],
        },
        {
            "id": "scen_002",
            "title": "Austin Creative Reputation Flywheel",
            "horizon": "3-5yr",
            "likelihood": "possible",
            "summary": (
                "Theo compounds visibility in Austin by pairing portfolio output with "
                "consistent relationship follow-up, turning community trust into repeat "
                "opportunities."
            ),
            "tags": ["austin", "reputation", "portfolio", "community"],
            "pattern_ids": [
                "social_signal_alignment",
                "creative_compounding",
                "relationship_driven_pipeline",
            ],
        },
        {
            "id": "scen_003",
            "title": "Sustainable ADHD-Compatible Studio Path",
            "horizon": "5-10yr",
            "likelihood": "aspirational",
            "summary": (
                "Theo builds a studio cadence around ADHD-compatible execution: fewer "
                "context switches, shorter admin loops, and high-intensity creative "
                "windows that sustain momentum."
            ),
            "tags": ["adhd", "sustainability", "studio", "systems"],
            "pattern_ids": [
                "adhd_execution_constraints",
                "energy_window_scheduling",
                "admin_friction_reduction",
            ],
        },
    ]


def _actions_by_scenario() -> dict[str, list[dict[str, Any]]]:
    return {
        "scen_001": [
            {
                "action": (
                    "Send a pricing follow-up on Theo's recent high-value lead and anchor "
                    "the next quote above the last $2,200 invoice."
                ),
                "rationale": (
                    "Theo already converted at $2,200 (t_0120); repeating that confidence loop "
                    "directly attacks undercharging drift."
                ),
                "data_ref": "t_0120",
                "pattern_id": "learning_vs_conversion_mismatch",
                "compound_summary": "Higher-ticket repeat closes stabilize monthly cash flow.",
            },
            {
                "action": (
                    "Block one 45-minute client onboarding/review slot this week mirroring the "
                    "successful onboarding cadence."
                ),
                "rationale": (
                    "cal_0078 shows onboarding calls are already working; repeating the pattern "
                    "converts intent into pipeline throughput."
                ),
                "data_ref": "cal_0078",
                "pattern_id": "conversion_follow_through",
                "compound_summary": "Regular onboarding windows shorten sales cycle latency.",
            },
            {
                "action": (
                    "Run a 20-minute debt review and transfer above-minimum payment this cycle."
                ),
                "rationale": (
                    "ll_0142 captures financial anxiety from minimum-only payments; one concrete "
                    "review loop lowers stress and restores execution bandwidth."
                ),
                "data_ref": "ll_0142",
                "pattern_id": "financial_stress_triangulation",
                "compound_summary": "Reduced debt pressure improves decision quality under load.",
            },
        ],
        "scen_002": [
            {
                "action": (
                    "Draft and queue two Austin-facing progress posts tied to measurable portfolio milestones."
                ),
                "rationale": (
                    "c_0001 reveals pricing-confidence tension; public milestone narratives close the "
                    "gap between internal doubt and external trust."
                ),
                "data_ref": "c_0001",
                "pattern_id": "public_private_delta",
                "compound_summary": "Trust compounding increases inbound referrals.",
            },
            {
                "action": "Set three lead follow-up rows in Notion with concrete due dates this week.",
                "rationale": (
                    "Pipeline consistency drives reputation flywheel more than one-off bursts."
                ),
                "data_ref": "cal_0078",
                "pattern_id": "relationship_driven_pipeline",
                "compound_summary": "Scheduled follow-ups convert weak ties into warm opportunities.",
            },
            {
                "action": (
                    "Ship one portfolio-ready challenge brief in Figma and share outcome recap publicly."
                ),
                "rationale": "Visible output creates social proof that supports higher-rate positioning.",
                "data_ref": "t_0120",
                "pattern_id": "creative_compounding",
                "compound_summary": "Portfolio cadence raises both confidence and close rate.",
            },
        ],
        "scen_003": [
            {
                "action": "Schedule two protected deep-work blocks at UT Library for high-focus creative output.",
                "rationale": (
                    "ADHD-compatible environmental constraints increase completion probability."
                ),
                "data_ref": "cal_0078",
                "pattern_id": "adhd_execution_constraints",
                "compound_summary": "Predictable focus windows improve weekly output reliability.",
            },
            {
                "action": "Create one 25-minute admin sprint for invoicing and follow-up cleanup.",
                "rationale": "Short admin loops reduce avoidance and keep financial ops from piling up.",
                "data_ref": "ll_0142",
                "pattern_id": "admin_friction_reduction",
                "compound_summary": "Lower admin backlog protects creative energy for billable work.",
            },
            {
                "action": "Document one repeatable studio ritual in Notion and apply it for seven days.",
                "rationale": (
                    "Systemizing execution converts sporadic motivation into stable studio behavior."
                ),
                "data_ref": "c_0001",
                "pattern_id": "energy_window_scheduling",
                "compound_summary": "Ritual consistency compounds into sustainable long-horizon growth.",
            },
        ],
    }


def generate_demo_actions(scenario_id: str, persona_id: str = "p05") -> dict[str, Any]:
    if persona_id != "p05":
        return {"scenario_id": scenario_id, "actions": []}
    scenario_id = normalize_demo_scenario_id(scenario_id)
    actions = _actions_by_scenario().get(scenario_id, [])
    return {"scenario_id": scenario_id, "actions": actions}


def generate_value_signals(persona_id: str = "p05") -> dict[str, Any]:
    if persona_id != "p05":
        return {}
    return {
        "public_private_delta": {
            "signal": "Public confidence is ahead of private certainty.",
            "evidence_refs": ["c_0001"],
        },
        "learning_vs_conversion_mismatch": {
            "signal": "Learning intensity outpaces direct revenue conversion loops.",
            "evidence_refs": ["t_0120", "cal_0078"],
        },
        "financial_stress_triangulation": {
            "signal": "Debt stress is an execution drag, not just a budgeting issue.",
            "evidence_refs": ["ll_0142", "t_0120"],
        },
        "adhd_execution_constraints": {
            "signal": "Execution improves when tasks are chunked and environment-scaffolded.",
            "evidence_refs": ["cal_0078", "c_0001"],
        },
    }
