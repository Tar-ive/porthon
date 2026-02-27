"""
Cross-Platform Personality Profiler
Mathematical framework for multi-source behavioral analysis.
Based on Rewind's Profiler Agent: https://github.com/Tar-ive/rewind

Data sources: persona, lifelog, conversations, transactions,
              emails, calendar, social_posts

v2: Dynamic scoring dimensions per persona type.
    Each persona type gets the dimensions most relevant to them
    rather than a one-size-fits-all set of scores.
"""

import math
import statistics
from dataclasses import dataclass, field
from typing import Any, Optional

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

DECAY_FACTOR    = 0.85   # Recency decay (0–1); higher = slower fade
SLIDING_WINDOW  = 14     # Days of memory
TEMPERATURE     = 8.0    # Sigmoid sharpness; higher = more bimodal

# Source weights: (execution_weight, growth_weight, self_awareness_weight)
SOURCE_WEIGHTS = {
    "persona":       (0.10, 0.05, 0.10),
    "lifelog":       (0.20, 0.15, 0.25),
    "conversations": (0.10, 0.20, 0.25),  # AI convos = most honest signal
    "transactions":  (0.25, 0.15, 0.10),
    "emails":        (0.15, 0.10, 0.10),
    "calendar":      (0.10, 0.20, 0.05),
    "social_posts":  (0.10, 0.15, 0.15),
}

# ── NEW v2: Persona types and their active scoring dimensions ──────────────
#
# Each persona type gets 5 dimensions. Execution + Growth + Self-Awareness
# are universal. The last two slots are persona-specific.
#
# Reasoning:
#   freelancer   → Financial Stress matters; ADHD pattern is behaviorally
#                  relevant at solo-operator scale.
#   vc_investor  → Already loaded, so raw financial stress is low-signal.
#                  Business Stress (portfolio risk, deal pressure) and
#                  Network Value (relationship leverage) matter instead.
#   founder      → Innovation Velocity (idea-to-ship speed) and Resilience
#                  (bounce-back from setbacks) are the relevant differentiators.
#   executive    → Leadership Bandwidth and Strategic Clarity replace
#                  the individual-contributor metrics.
#   creator      → Audience Growth Rate and Creative Output replace
#                  financial/ADHD metrics.
#   default      → Falls back to freelancer set.

PERSONA_DIMENSIONS = {
    "freelancer":  ["execution", "growth", "self_awareness", "financial_stress", "adhd_indicator"],
    "vc_investor": ["execution", "growth", "self_awareness", "business_stress",  "network_value"],
    "founder":     ["execution", "growth", "self_awareness", "innovation_velocity", "resilience"],
    "executive":   ["execution", "growth", "self_awareness", "leadership_bandwidth", "strategic_clarity"],
    "creator":     ["execution", "growth", "self_awareness", "audience_growth", "creative_output"],
    "default":     ["execution", "growth", "self_awareness", "financial_stress", "adhd_indicator"],
}

DIMENSION_LABELS = {
    "execution":           "Execution",
    "growth":              "Growth",
    "self_awareness":      "Self-Awareness",
    "financial_stress":    "Financial Stress",
    "adhd_indicator":      "ADHD Indicator",
    "business_stress":     "Business Stress",
    "network_value":       "Network Value",
    "innovation_velocity": "Innovation Velocity",
    "resilience":          "Resilience",
    "leadership_bandwidth":"Leadership Bandwidth",
    "strategic_clarity":   "Strategic Clarity",
    "audience_growth":     "Audience Growth",
    "creative_output":     "Creative Output",
}

# ═══════════════════════════════════════════════════════════════════════════
# CORE MATH — unchanged from v1
# ═══════════════════════════════════════════════════════════════════════════

def decay_weight(age_days: int, decay: float = DECAY_FACTOR,
                 window: int = SLIDING_WINDOW) -> float:
    """Exponential decay: weight = decay_factor ^ age_days"""
    return decay ** min(max(0, age_days), window)


def weighted_mean(values: list[float], weights: Optional[list[float]] = None) -> float:
    """Weighted average; uniform weights if none provided."""
    if not values:
        return 0.0
    if weights is None:
        weights = [1.0] * len(values)
    return sum(v * w for v, w in zip(values, weights)) / sum(weights)


def sigmoid(x: float, temperature: float = TEMPERATURE) -> float:
    """
    Temperature-controlled sigmoid normalization.
    T=8 creates a bimodal distribution — weak signals crushed, strong amplified.
      x=0.10 → 0.04  |  x=0.50 → 0.50  |  x=0.90 → 0.96
    """
    x = max(-20.0, min(20.0, temperature * (x - 0.5)))
    return 1.0 / (1.0 + math.exp(-x))


def normalize(raw: float) -> float:
    """Apply temperature-controlled sigmoid and round to 4dp."""
    return round(sigmoid(raw), 4)


def compute_variance(values: list[float]) -> float:
    """Statistical variance of a list."""
    return statistics.variance(values) if len(values) >= 2 else 0.0


# ═══════════════════════════════════════════════════════════════════════════
# UNIVERSAL DIMENSIONS (all persona types)
# ═══════════════════════════════════════════════════════════════════════════

def compute_execution_signal(data: dict[str, Any]) -> float:
    """
    How effectively do they get things done?
    Weighted: transactions 40% · calendar 30% · emails 30%
    """
    signals = []
    tx = data.get("transactions", {})
    if tx.get("revenue", {}).get("count", 0) > 0:
        win_rate = tx["revenue"]["count"] / max(tx.get("invoice_win_rate", 0.125) * 200, 1)
        signals.append(("invoice_win_rate", win_rate, 0.4))
    cal = data.get("calendar", {})
    if cal.get("total_events", 0) > 0:
        signals.append(("calendar_adherence", min(0.9, cal["total_events"] / 100), 0.3))
    email = data.get("emails", {})
    if email.get("total_emails", 0) > 0:
        signals.append(("response_speed", 0.6, 0.3))
    if signals:
        tw = sum(w for _, _, w in signals)
        return sum(s * w for _, s, w in signals) / tw
    return 0.5


def compute_growth_signal(data: dict[str, Any]) -> float:
    """
    Are they improving over time?
    Weighted: transactions 35% · lifelog 35% · calendar 30%
    """
    signals = []
    tx = data.get("transactions", {})
    if tx.get("revenue", {}).get("total", 0) > 0:
        signals.append(("revenue_growth", min(1.0, tx.get("avg_monthly_revenue", 0) / 6000), 0.35))
    ll = data.get("lifelog", {})
    themes = ll.get("themes", {})
    learning = themes.get("ai_usage", 0) + themes.get("creativity", 0)
    if learning > 0:
        signals.append(("learning_investment", min(1.0, learning / 30), 0.35))
    cal = data.get("calendar", {})
    if cal.get("total_events", 0) > 0:
        signals.append(("learning_intensity", min(1.0, (cal["total_events"] / 10) / 10), 0.30))
    if signals:
        tw = sum(w for _, _, w in signals)
        return sum(s * w for _, s, w in signals) / tw
    return 0.5


def compute_self_awareness_signal(data: dict[str, Any]) -> float:
    """
    Alignment between claimed self, AI-honest self, and behavioral patterns.
    """
    conv = data.get("conversations", {})
    ai_honesty = min(1.0, conv.get("total_sessions", 0) / 10)
    ll = data.get("lifelog", {})
    diversity = len(ll.get("themes", {})) / 15
    return ai_honesty * 0.5 + min(1.0, diversity) * 0.5


# ═══════════════════════════════════════════════════════════════════════════
# PERSONA-SPECIFIC DIMENSIONS — v2 additions
# ═══════════════════════════════════════════════════════════════════════════

# ── freelancer ─────────────────────────────────────────────────────────────

def compute_financial_stress_signal(data: dict[str, Any]) -> float:
    """
    Financial anxiety. 0=calm, 1=extreme stress.
    Sources: debt level (30%) · worry frequency (35%) · spending ratio (35%)
    """
    signals = []
    debt = data.get("persona", {}).get("debt", 0)
    if debt > 0:
        signals.append(("debt_level", min(1.0, debt / 20000), 0.30))
    ll = data.get("lifelog", {})
    finance_mentions = ll.get("themes", {}).get("finances", 0)
    if finance_mentions > 0:
        signals.append(("financial_worry", min(1.0, finance_mentions / 20), 0.35))
    tx = data.get("transactions", {})
    revenue = tx.get("revenue", {}).get("total", 0)
    expenses = tx.get("subscriptions", {}).get("total", 0) + tx.get("rent", {}).get("total", 0)
    if revenue > 0:
        ratio = expenses / revenue
        signals.append(("spending_stress", min(1.0, max(0, (ratio - 0.5) * 2)), 0.35))
    if signals:
        tw = sum(w for _, _, w in signals)
        return sum(s * w for _, s, w in signals) / tw
    return 0.3


def compute_adhd_indicator_signal(data: dict[str, Any]) -> float:
    """
    ADHD-consistent behavioral patterns (not a diagnosis).
    Sources: self-report (25%) · theme variety (25%) · schedule irregularity (25%) · impulse indicator (25%)
    """
    signals = []
    if data.get("persona", {}).get("has_adhd", False):
        signals.append(("self_reported", 0.9, 0.25))
    ll = data.get("lifelog", {})
    variety = len(ll.get("themes", {})) / 15
    if variety > 0.5:
        signals.append(("attention_variety", variety, 0.25))
    cal = data.get("calendar", {})
    if cal.get("total_events", 0) > 0:
        signals.append(("schedule_irregularity", min(1.0, len(cal.get("by_type", {})) / 5), 0.25))
    signals.append(("impulse_indicator", 0.5, 0.25))
    tw = sum(w for _, _, w in signals)
    return sum(s * w for _, s, w in signals) / tw


# ── vc_investor ─────────────────────────────────────────────────────────────

def compute_business_stress_signal(data: dict[str, Any]) -> float:
    """
    Portfolio/deal pressure rather than personal financial anxiety.
    Sources: email volume (proxy for deal flow) · calendar density · lifelog worry tags.

    For VCs, financial wealth is assumed; stress comes from portfolio risk,
    LP pressure, and competitive deal flow.
    """
    signals = []
    email = data.get("emails", {})
    # High email volume = high deal/portfolio pressure
    email_density = min(1.0, email.get("total_emails", 0) / 200)
    signals.append(("deal_flow_pressure", email_density, 0.35))
    cal = data.get("calendar", {})
    # Calendar overload = business stress
    cal_density = min(1.0, cal.get("total_events", 0) / 150)
    signals.append(("calendar_overload", cal_density, 0.30))
    ll = data.get("lifelog", {})
    anxiety_tags = ll.get("tag_distribution", {}).get("anxiety", 0)
    signals.append(("anxiety_signal", min(1.0, anxiety_tags / 20), 0.35))
    tw = sum(w for _, _, w in signals)
    return sum(s * w for _, s, w in signals) / tw


def compute_network_value_signal(data: dict[str, Any]) -> float:
    """
    Relationship leverage. High = strong, high-quality network.
    Sources: email outreach rate · social presence · calendar meeting density.
    """
    signals = []
    email = data.get("emails", {})
    sent = email.get("by_type", {}).get("sent", 0)
    total = email.get("total_emails", 1)
    signals.append(("outreach_rate", min(1.0, sent / max(total, 1)), 0.35))
    social = data.get("social", {})
    signals.append(("social_presence", min(1.0, social.get("total_posts", 0) / 100), 0.30))
    cal = data.get("calendar", {})
    signals.append(("meeting_density", min(1.0, cal.get("total_events", 0) / 80), 0.35))
    tw = sum(w for _, _, w in signals)
    return sum(s * w for _, s, w in signals) / tw


# ── founder ─────────────────────────────────────────────────────────────────

def compute_innovation_velocity_signal(data: dict[str, Any]) -> float:
    """
    Speed of idea-to-output. High = rapid prototyping and shipping.
    Sources: AI tool usage · creativity themes · transaction frequency (proxy for shipping).
    """
    signals = []
    ll = data.get("lifelog", {})
    themes = ll.get("themes", {})
    ai_usage = themes.get("ai_usage", 0)
    creativity = themes.get("creativity", 0)
    signals.append(("ai_leverage", min(1.0, ai_usage / 20), 0.35))
    signals.append(("creativity_output", min(1.0, creativity / 15), 0.30))
    tx = data.get("transactions", {})
    ship_rate = min(1.0, tx.get("revenue", {}).get("count", 0) / 30)
    signals.append(("shipping_rate", ship_rate, 0.35))
    tw = sum(w for _, _, w in signals)
    return sum(s * w for _, s, w in signals) / tw


def compute_resilience_signal(data: dict[str, Any]) -> float:
    """
    Bounce-back from setbacks. High = maintains output despite failures.
    Sources: milestone tags vs anxiety tags ratio · conversation depth · win rate over time.
    """
    ll = data.get("lifelog", {})
    tags = ll.get("tag_distribution", {})
    milestones = tags.get("milestone", 0)
    anxiety = tags.get("anxiety", 0)
    # Resilience = wins persisting despite anxiety
    ratio = milestones / max(anxiety + 1, 1)
    resilience_from_log = min(1.0, ratio / 3)
    conv = data.get("conversations", {})
    depth = min(1.0, conv.get("total_sessions", 0) / 10)
    tx = data.get("transactions", {})
    win_rate = tx.get("invoice_win_rate", 0.1)
    return resilience_from_log * 0.4 + depth * 0.3 + win_rate * 0.3


# ── executive ───────────────────────────────────────────────────────────────

def compute_leadership_bandwidth_signal(data: dict[str, Any]) -> float:
    """
    Capacity to lead others. High = high meeting load, high email output, diverse calendar.
    """
    cal = data.get("calendar", {})
    email = data.get("emails", {})
    sent = email.get("by_type", {}).get("sent", 0)
    cal_load = min(1.0, cal.get("total_events", 0) / 120)
    email_output = min(1.0, sent / 60)
    return cal_load * 0.5 + email_output * 0.5


def compute_strategic_clarity_signal(data: dict[str, Any]) -> float:
    """
    Coherence of goals vs behaviors. Low delta between stated goals and actual calendar/spend.
    Sources: goal-to-behavior alignment (estimated from lifelog focus vs persona goals).
    """
    ll = data.get("lifelog", {})
    themes = ll.get("themes", {})
    work_focus = themes.get("work_freelance", 0) + themes.get("ai_usage", 0)
    total_entries = ll.get("total_entries", 1)
    focus_ratio = work_focus / max(total_entries, 1)
    conv = data.get("conversations", {})
    session_depth = min(1.0, conv.get("total_sessions", 0) / 10)
    return min(1.0, focus_ratio * 2) * 0.6 + session_depth * 0.4


# ── creator ─────────────────────────────────────────────────────────────────

def compute_audience_growth_signal(data: dict[str, Any]) -> float:
    """
    Rate of audience/following expansion.
    Sources: social post volume · follower-proxy engagement · cross-platform presence.
    """
    social = data.get("social", {})
    post_rate = min(1.0, social.get("total_posts", 0) / 60)
    platforms = len(social.get("by_platform", {}))
    platform_diversity = min(1.0, platforms / 4)
    conv = data.get("conversations", {})
    ai_collab = min(1.0, conv.get("total_sessions", 0) / 8)
    return post_rate * 0.45 + platform_diversity * 0.30 + ai_collab * 0.25


def compute_creative_output_signal(data: dict[str, Any]) -> float:
    """
    Volume and consistency of creative production.
    Sources: creativity themes · AI tool usage · portfolio mentions.
    """
    ll = data.get("lifelog", {})
    themes = ll.get("themes", {})
    creativity = themes.get("creativity", 0)
    ai_usage = themes.get("ai_usage", 0)
    tags = ll.get("tag_distribution", {})
    portfolio_mentions = tags.get("portfolio", 0)
    return (
        min(1.0, creativity / 15) * 0.35 +
        min(1.0, ai_usage / 15) * 0.30 +
        min(1.0, portfolio_mentions / 20) * 0.35
    )


# ═══════════════════════════════════════════════════════════════════════════
# DIMENSION ROUTER — maps dimension name → compute function
# ═══════════════════════════════════════════════════════════════════════════

DIMENSION_FUNCTIONS = {
    "execution":            compute_execution_signal,
    "growth":               compute_growth_signal,
    "self_awareness":       compute_self_awareness_signal,
    "financial_stress":     compute_financial_stress_signal,
    "adhd_indicator":       compute_adhd_indicator_signal,
    "business_stress":      compute_business_stress_signal,
    "network_value":        compute_network_value_signal,
    "innovation_velocity":  compute_innovation_velocity_signal,
    "resilience":           compute_resilience_signal,
    "leadership_bandwidth": compute_leadership_bandwidth_signal,
    "strategic_clarity":    compute_strategic_clarity_signal,
    "audience_growth":      compute_audience_growth_signal,
    "creative_output":      compute_creative_output_signal,
}


# ═══════════════════════════════════════════════════════════════════════════
# ARCHETYPE CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════

ARCHETYPES = {
    ("high", "high"): ("compounding_builder",  "Elite shipper + steep learning curve"),
    ("high", "low"):  ("reliable_operator",    "Consistent but plateauing"),
    ("low",  "high"): ("emerging_talent",      "Low output, rapid improvement"),
    ("low",  "low"):  ("at_risk",              "Low completion, no growth trend"),
}

def classify_archetype(exec_score: float, growth_score: float) -> dict[str, str]:
    e = "high" if exec_score >= 0.70 else "low"
    g = "high" if growth_score >= 0.65 else "low"
    name, desc = ARCHETYPES[(e, g)]
    return {"archetype": name, "description": desc}


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PROFILER CLASS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CrossPlatformProfiler:
    """
    Multi-source personality profiler with dynamic, persona-aware dimensions.

    persona_type: one of freelancer | vc_investor | founder | executive | creator | default
    """
    data: dict[str, Any]
    persona_type: str = "default"

    def _dimensions(self) -> list[str]:
        """Return the active dimension list for this persona type."""
        return PERSONA_DIMENSIONS.get(self.persona_type, PERSONA_DIMENSIONS["default"])

    def compute_raw_signals(self) -> dict[str, float]:
        """Compute raw (pre-sigmoid) scores for active dimensions."""
        return {
            dim: DIMENSION_FUNCTIONS[dim](self.data)
            for dim in self._dimensions()
        }

    def compute_normalized_profile(self) -> dict[str, float]:
        """Apply temperature-controlled sigmoid normalization."""
        return {k: normalize(v) for k, v in self.compute_raw_signals().items()}

    def compute_archetype(self) -> dict[str, Any]:
        """Full profile: normalized scores + archetype classification."""
        normed = self.compute_normalized_profile()
        arch = classify_archetype(normed["execution"], normed["growth"])
        return {
            "persona_type":    self.persona_type,
            "dimensions":      {DIMENSION_LABELS[k]: v for k, v in normed.items()},
            "archetype":       arch["archetype"],
            "arch_description": arch["description"],
            "execution_score": normed["execution"],
            "growth_score":    normed["growth"],
        }

    def compute_cross_source_deltas(self) -> dict[str, float]:
        """
        Dissonance between data sources.
        High delta = coaching/intervention opportunity.
        """
        import re
        deltas = {}

        # Social activity vs AI session activity
        social_rate = self.data.get("social", {}).get("total_posts", 0) / 50
        ai_rate     = self.data.get("conversations", {}).get("total_sessions", 0) / 10
        if social_rate > 0 and ai_rate > 0:
            deltas["social_vs_ai_dissonance"] = abs(social_rate - ai_rate)

        # Claimed vs actual income
        claimed_str = self.data.get("persona", {}).get("income_approx", "$0")
        actual = self.data.get("transactions", {}).get("avg_monthly_revenue", 0) * 12
        m = re.search(r'\$(\d+,?\d*)', claimed_str)
        if m and actual > 0:
            claimed = float(m.group(1).replace(",", ""))
            if claimed > 0:
                deltas["income_expectation_gap"] = abs(claimed - actual) / claimed

        # Email sent/received ratio (proxy for relational balance)
        email = self.data.get("emails", {})
        sent  = email.get("by_type", {}).get("sent", 0)
        inbox = email.get("by_type", {}).get("inbox", 0)
        if sent + inbox > 0:
            deltas["email_send_receive_ratio"] = sent / max(inbox, 1)

        return deltas

    def full_report(self) -> dict[str, Any]:
        """Convenience: returns everything in one call."""
        return {
            "profile": self.compute_archetype(),
            "deltas":  self.compute_cross_source_deltas(),
            "raw":     self.compute_raw_signals(),
        }


# ═══════════════════════════════════════════════════════════════════════════
# CLI USAGE
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json, sys

    persona_type = sys.argv[1] if len(sys.argv) > 1 else "freelancer"

    with open("data/summaries/master_profile.json") as f:
        raw = json.load(f)

    data = {
        "persona": {
            "debt":          raw.get("debt", 0),
            "has_adhd":      raw.get("has_adhd", False),
            "income_approx": raw.get("income_approx", "$0"),
        },
        **raw["data_sources"],
    }

    profiler = CrossPlatformProfiler(data, persona_type=persona_type)
    report   = profiler.full_report()

    print(f"\n═══ PROFILE [{persona_type.upper()}] ═══")
    for label, score in report["profile"]["dimensions"].items():
        bar = "█" * int(score * 20)
        print(f"  {label:<22} {score:.3f}  {bar}")

    print(f"\n  Archetype: {report['profile']['archetype']}")
    print(f"  {report['profile']['arch_description']}")

    print("\n═══ CROSS-SOURCE DELTAS ═══")
    for k, v in report["deltas"].items():
        print(f"  {k}: {v:.1%}")
