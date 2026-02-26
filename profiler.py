"""
Cross-Platform Personality Profiler

Mathematical framework for multi-source behavioral analysis.
Based on Rewind's Profiler Agent: https://github.com/Tar-ive/rewind

Data sources: persona, lifelog, conversations, transactions, 
              emails, calendar, social_posts
"""

import math
import statistics
from dataclasses import dataclass
from typing import Any, Optional

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

DECAY_FACTOR = 0.85      # How fast recent memory fades (0-1)
SLIDING_WINDOW = 14     # Days to consider
TEMPERATURE = 8.0       # Exclusive normalization strength (higher = more selective)

# Source weights: (execution_weight, growth_weight, self_awareness_weight)
SOURCE_WEIGHTS = {
    "persona":       (0.10, 0.05, 0.10),
    "lifelog":       (0.20, 0.15, 0.25),
    "conversations": (0.10, 0.20, 0.25),  # AI convos = most honest
    "transactions":  (0.25, 0.15, 0.10),
    "emails":        (0.15, 0.10, 0.10),
    "calendar":      (0.10, 0.20, 0.05),
    "social_posts":  (0.10, 0.15, 0.15),
}

# ═══════════════════════════════════════════════════════════════════════════
# CORE MATH FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def decay_weight(age_days: int, decay: float = DECAY_FACTOR, 
                 window: int = SLIDING_WINDOW) -> float:
    """
    Exponential decay: weight = decay_factor ^ age_days
    
    Example with decay=0.85, window=14:
    Day 0 (oldest):  0.85^13 = 0.12
    Day 7:          0.85^6  = 0.38
    Day 13 (newest): 0.85^0  = 1.00
    """
    age_days = max(0, age_days)
    return decay ** min(age_days, window)


def weighted_mean(values: list[float], weights: Optional[list[float]] = None) -> float:
    """
    Weighted average. If weights not provided, uses uniform weights.
    """
    if not values:
        return 0.0
    
    if weights is None:
        weights = [1.0] * len(values)
    
    return sum(v * w for v, w in zip(values, weights)) / sum(weights)


def sigmoid(x: float, temperature: float = TEMPERATURE) -> float:
    """
    Temperature-controlled sigmoid normalization.
    
    At T = 8.0:
    x=0.10 → 0.04 (crushed - weak signal suppressed)
    x=0.30 → 0.17 
    x=0.50 → 0.50 (inflection - unchanged)
    x=0.70 → 0.83 
    x=0.90 → 0.96 (amplified - strong signal enhanced)
    
    This creates bimodal distribution - only genuine signals survive.
    """
    # Clamp to prevent overflow
    x = max(-20.0, min(20.0, temperature * (x - 0.5)))
    return 1.0 / (1.0 + math.exp(-x))


def normalize_vector(raw_score: float, temperature: float = TEMPERATURE) -> float:
    """Apply temperature-controlled sigmoid normalization."""
    return round(sigmoid(raw_score, temperature), 4)


def compute_variance(values: list[float]) -> float:
    """Statistical variance of a list."""
    if len(values) < 2:
        return 0.0
    return statistics.variance(values)


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL COMPUTATION PER DIMENSION
# ═══════════════════════════════════════════════════════════════════════════

def compute_execution_signal(data: dict[str, Any]) -> float:
    """
    How effectively do they get things done?
    
    Sources: 
    - transactions: invoice win rate
    - calendar: commitment adherence
    - emails: response time quality
    """
    signals = []
    
    # From transactions: invoice win rate
    tx = data.get("transactions", {})
    if tx.get("revenue", {}).get("count", 0) > 0:
        invoices_sent = tx.get("invoice_win_rate", 0.125) * 200  # Estimate
        invoices_won = tx["revenue"]["count"]
        win_rate = invoices_won / max(invoices_sent, 1)
        signals.append(("invoice_win_rate", win_rate, 0.4))
    
    # From calendar: show rate
    cal = data.get("calendar", {})
    if cal.get("total_events", 0) > 0:
        # Estimate show rate from event count density
        show_rate = min(0.9, cal["total_events"] / 100)
        signals.append(("calendar_adherence", show_rate, 0.3))
    
    # From emails: response rate
    email = data.get("emails", {})
    if email.get("total_emails", 0) > 0:
        response_rate = 0.6  # Default estimate
        signals.append(("response_speed", response_rate, 0.3))
    
    if signals:
        total_weight = sum(w for _, _, w in signals)
        return sum(s * w for _, s, w in signals) / total_weight
    
    return 0.5


def compute_growth_signal(data: dict[str, Any]) -> float:
    """
    Are they improving over time?
    
    Sources:
    - transactions: revenue trend
    - lifelog: win/loss ratio
    - calendar: learning investment
    """
    signals = []
    
    # From transactions: revenue
    tx = data.get("transactions", {})
    if tx.get("revenue", {}).get("total", 0) > 0:
        monthly = tx.get("avg_monthly_revenue", 0)
        # Normalize: $3000/month = 0.5, higher is better
        growth = min(1.0, monthly / 6000)
        signals.append(("revenue_growth", growth, 0.35))
    
    # From lifelog: themes
    ll = data.get("lifelog", {})
    themes = ll.get("themes", {})
    learning_mentions = themes.get("ai_usage", 0) + themes.get("creativity", 0)
    if learning_mentions > 0:
        learning_intensity = min(1.0, learning_mentions / 30)
        signals.append(("learning_investment", learning_intensity, 0.35))
    
    # From calendar: learning sessions
    cal = data.get("calendar", {})
    if cal.get("total_events", 0) > 0:
        # Assume some events are learning-related
        learning_events = cal["total_events"] / 10  # Estimate
        signals.append(("learning_intensity", min(1.0, learning_events / 10), 0.30))
    
    if signals:
        total_weight = sum(w for _, _, w in signals)
        return sum(s * w for _, s, w in signals) / total_weight
    
    return 0.5


def compute_self_awareness_signal(data: dict[str, Any]) -> float:
    """
    How honest is their self-perception?
    
    Compare:
    - persona: stated identity
    - AI conversations: unfiltered
    - lifelog: behavioral patterns
    """
    # Baseline: what they claim (persona)
    persona = data.get("persona", {})
    claimed_coherence = 0.6  # Default
    
    # What they tell AI (most honest)
    conv = data.get("conversations", {})
    ai_honesty = min(1.0, conv.get("total_sessions", 0) / 10)
    
    # What lifelog shows
    ll = data.get("lifelog", {})
    themes = ll.get("themes", {})
    # More diverse themes = more self-aware
    diversity = len(themes) / 15
    behavioral_awareness = min(1.0, diversity)
    
    # Self-awareness = alignment between claimed and AI + behavioral
    return (ai_honesty * 0.5 + behavioral_awareness * 0.5)


def compute_financial_stress_signal(data: dict[str, Any]) -> float:
    """
    Financial anxiety across sources.
    0 = no stress, 1 = extreme stress
    """
    signals = []
    
    # From persona: debt level
    debt = data.get("persona", {}).get("debt", 0)
    if debt > 0:
        debt_stress = min(1.0, debt / 20000)  # $20k = max
        signals.append(("debt_level", debt_stress, 0.30))
    
    # From lifelog: financial themes
    ll = data.get("lifelog", {})
    themes = ll.get("themes", {})
    finance_mentions = themes.get("finances", 0)
    if finance_mentions > 0:
        worry_rate = min(1.0, finance_mentions / 20)
        signals.append(("financial_worry", worry_rate, 0.35))
    
    # From transactions: spending vs income
    tx = data.get("transactions", {})
    revenue = tx.get("revenue", {}).get("total", 0)
    expenses = tx.get("subscriptions", {}).get("total", 0) + tx.get("rent", {}).get("total", 0)
    if revenue > 0:
        spending_ratio = expenses / revenue
        stress = min(1.0, max(0, spending_ratio - 0.5) * 2)
        signals.append(("spending_stress", stress, 0.35))
    
    if signals:
        total_weight = sum(w for _, _, w in signals)
        return sum(s * w for _, s, w in signals) / total_weight
    
    return 0.3


def compute_adhd_indicator_signal(data: dict[str, Any]) -> float:
    """
    ADHD indicators across sources (not diagnosis).
    """
    signals = []
    
    # From persona: self-reported ADHD
    if data.get("persona", {}).get("has_adhd", False):
        signals.append(("self_reported_adhd", 0.9, 0.25))
    
    # From lifelog: variety of themes (scattered attention)
    ll = data.get("lifelog", {})
    themes = ll.get("themes", {})
    variety = len(themes) / 15
    if variety > 0.5:
        signals.append(("attention_variety", variety, 0.25))
    
    # From calendar: event irregularity
    cal = data.get("calendar", {})
    if cal.get("total_events", 0) > 0:
        # Many different types of events = scattered
        event_types = len(cal.get("by_type", {}))
        irregularity = min(1.0, event_types / 5)
        signals.append(("schedule_irregularity", irregularity, 0.25))
    
    # From transactions: impulse spending
    tx = data.get("transactions", {})
    # Assuming some transactions are impulse
    signals.append(("impulse_indicator", 0.5, 0.25))
    
    if signals:
        total_weight = sum(w for _, _, w in signals)
        return sum(s * w for _, s, w in signals) / total_weight
    
    return 0.3


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PROFILER CLASS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CrossPlatformProfiler:
    """Multi-source personality profiler."""
    
    data: dict[str, Any]
    
    def compute_all_signals(self) -> dict[str, float]:
        """Compute raw signals before normalization."""
        return {
            "execution_score": compute_execution_signal(self.data),
            "growth_score": compute_growth_signal(self.data),
            "self_awareness_score": compute_self_awareness_signal(self.data),
            "financial_stress_score": compute_financial_stress_signal(self.data),
            "adhd_indicator_score": compute_adhd_indicator_signal(self.data),
        }
    
    def compute_normalized_profile(self) -> dict[str, float]:
        """Apply temperature-controlled sigmoid normalization."""
        raw = self.compute_all_signals()
        return {
            key: normalize_vector(value) 
            for key, value in raw.items()
        }
    
    def compute_archetype(self) -> dict[str, Any]:
        """
        Classify into archetype based on execution vs growth.
        
        Uses the 4-quadrant model:
        - High Exec + High Growth = Compounding Builder
        - High Exec + Low Growth = Reliable Operator
        - Low Exec + High Growth = Emerging Talent
        - Low Exec + Low Growth = At Risk
        """
        normalized = self.compute_normalized_profile()
        
        exec_score = normalized["execution_score"]
        growth_score = normalized["growth_score"]
        
        # Apply thresholds (exclusive model)
        if exec_score >= 0.85 and growth_score >= 0.80:
            archetype = "compounding_builder"
        elif exec_score >= 0.70 and growth_score < 0.65:
            archetype = "reliable_operator"
        elif growth_score >= 0.65 and exec_score < 0.70:
            archetype = "emerging_talent"
        else:
            archetype = "at_risk"
        
        return {
            "archetype": archetype,
            "execution_score": exec_score,
            "growth_score": growth_score,
            "self_awareness": normalized["self_awareness_score"],
            "financial_stress": normalized["financial_stress_score"],
            "adhd_indicator": normalized["adhd_indicator_score"],
        }
    
    def compute_cross_source_deltas(self) -> dict[str, float]:
        """
        Key innovation: measure dissonance between sources.
        
        delta = |source_a - source_b|
        
        High delta = potential coaching opportunity
        """
        deltas = {}
        
        # Social vs AI confidence
        social = self.data.get("social", {}).get("total_posts", 0) / 50
        ai = self.data.get("conversations", {}).get("total_sessions", 0) / 10
        if social > 0 and ai > 0:
            deltas["social_vs_ai_activity"] = abs(social - ai)
        
        # Claimed vs Actual income
        persona = self.data.get("persona", {})
        tx = self.data.get("transactions", {})
        claimed_income = persona.get("income_approx", "$0")
        actual_income = tx.get("avg_monthly_revenue", 0) * 12
        
        # Parse claimed income
        import re
        match = re.search(r'\$(\d+,?\d*)', claimed_income)
        if match:
            claimed = float(match.group(1).replace(',', ''))
            if claimed > 0 and actual_income > 0:
                deltas["income_expectation_delta"] = abs(claimed - actual_income) / claimed
        
        return deltas


# ═══════════════════════════════════════════════════════════════════════════
# USAGE EXAMPLE
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json
    
    # Load the condensed data
    with open('data/master_profile.json') as f:
        data = json.load(f)
    
    # Create profiler
    profiler = CrossPlatformProfiler(data)
    
    # Get profile
    profile = profiler.compute_archetype()
    deltas = profiler.compute_cross_source_deltas()
    
    print("═══ PERSONALITY PROFILE ═══")
    for k, v in profile.items():
        print(f"  {k}: {v}")
    
    print("\n═══ CROSS-SOURCE DELTAS ═══")
    for k, v in deltas.items():
        print(f"  {k}: {v:.2%}")
