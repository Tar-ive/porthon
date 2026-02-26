# Cross-Platform Personality Profiling

## Mathematical Framework for Multi-Source Behavioral Analysis

---

## The Core Insight

Different data sources reveal different facets of a person:

| Data Source | The Story It Tells | Psychological Construct |
|-------------|-------------------|------------------------|
| **Social Media** | The "performed" self — curated, aspirational, public-facing | *Presented Identity* |
| **Emails** | The "professional/relational" self — task-oriented, formal | *Instrumental Identity* |
| **AI Conversations** | The "unfiltered" self — curious, vulnerable, experimental | *Authentic Inner World* |
| **Transactions** | Behavioral reality — what they actually spend/do | *Economic Behavior* |
| **Calendar** | Time allocation truth — how they prioritize | *Behavioral Patterns* |
| **Lifelog** | The inner narrative — wins, losses, rumination | *Self-Concept* |

---

## Source: Rewind's Profiler Agent Math

This framework is adapted from [Tar-ive/rewind](https://github.com/Tar-ive/rewind/blob/main/backend/src/agents/profiler_agent.py).

### Core Equation 1: Exponential Decay Weighting

```
weight_i = decay_factor^(window_size - i)

Example with decay_factor = 0.85, window = 14 days:
Day 0 (oldest):  0.85^13 = 0.12
Day 7:          0.85^6  = 0.38
Day 13 (newest): 0.85^0  = 1.00
```

**Purpose:** Recent behavior matters more. Last week's actions > actions from 6 months ago.

**Python Implementation:**
```python
def decay_weight(age_days: int, decay: float = 0.85) -> float:
    """Exponential decay: weight = decay_factor ^ age_days"""
    age_days = max(0, age_days)
    return decay ** min(age_days, SLIDING_WINDOW)
```

---

### Core Equation 2: Temperature-Controlled Sigmoid (Adapted Softmax)

```
normalized(x) = 1 / (1 + exp(-T × (x - 0.5)))

At T = 8.0 (temperature = 8.0):
x=0.10 → 0.04 (crushed - weak signal suppressed)
x=0.30 → 0.17 
x=0.50 → 0.50 (inflection point - unchanged)
x=0.70 → 0.83 
x=0.90 → 0.96 (amplified - strong signal enhanced)
```

**Purpose:** Creates **bimodal distribution** — only genuine signals survive. Noise gets crushed, strong signals get amplified. This makes the classifier "exclusive."

**Python Implementation:**
```python
def sigmoid(x: float, temperature: float = 8.0) -> float:
    """Temperature-controlled sigmoid normalization"""
    x = max(-20.0, min(20.0, temperature * (x - 0.5)))
    return 1.0 / (1.0 + math.exp(-x))
```

---

### Core Equation 3: Weighted Mean with Decay

```
weighted_mean = Σ(value_i × weight_i) / Σ(weight_i)

Where weight_i uses exponential decay based on recency.
```

**Purpose:** Combine multiple signals while favoring recent observations.

**Python Implementation:**
```python
def weighted_mean(values: list[float], weights: list[float]) -> float:
    """Weighted average with optional decay"""
    if not values or not weights:
        return 0.0
    return sum(v * w for v, w in zip(values, weights)) / sum(weights)

def _apply_decay(self, values: list[float]) -> float:
    """Weighted mean with exponential recency decay."""
    if not values:
        return 0.0
    weights = [self._decay_weight(len(values) - 1 - i) for i in range(len(values))]
    total_w = sum(weights)
    if total_w == 0:
        return 0.0
    return sum(v * w for v, w in zip(values, weights)) / total_w
```

---

## Scoring Dimensions

### 1. Execution Score

**What it measures:** How effectively they get things done.

**Sources weighted:**
- Transactions (40%): Invoice win rate
- Calendar (30%): Commitment adherence
- Emails (30%): Response time quality

**Formula:**
```
execution = (invoice_win_rate × 0.4) + (calendar_adherence × 0.3) + (response_speed × 0.3)
```

---

### 2. Growth Score

**What it measures:** Are they improving over time?

**Sources weighted:**
- Transactions (35%): Revenue trend
- Lifelog (35%): Win/loss ratio with recency boost
- Calendar (30%): Learning investment

**Formula:**
```
growth = (revenue_trend × 0.35) + (win_ratio × 0.35) + (learning_intensity × 0.3)
```

---

### 3. Self-Awareness Score

**How honest is their self-perception?**

**Method:** Compare delta between sources:
- **Persona** (stated): What they claim
- **AI Conversations** (unfiltered): What they tell AI
- **Lifelog** (behavioral): What their actions show

**Formula:**
```
delta = |claimed - ai_honest|
awareness = 1.0 - delta
self_awareness = (awareness × 0.6 + behavioral × 0.4)
```

---

### 4. Financial Stress Score

**What it measures:** Financial anxiety across sources.

**Sources:**
- Persona: Debt level
- Lifelog: Frequency of financial worry mentions
- Transactions: Spending vs income ratio

**Formula:**
```
debt_stress = min(1.0, debt / 20000)  # $20k = max
worry_rate = min(1.0, worry_mentions / 10)
spending_stress = min(1.0, max(0, (spending/income - 0.5) × 2))

financial_stress = (debt_stress × 0.3) + (worry_rate × 0.35) + (spending_stress × 0.35)
```

---

### 5. ADHD Indicator Score

**What it measures:** Behavioral patterns associated with ADHD (not a diagnosis).

**Sources:**
- Persona: Self-reported ADHD
- Lifelog: Focus variance (high = ADHD-like)
- Calendar: Schedule irregularity
- Transactions: Impulse spending rate

**Formula:**
```
adhd_indicator = (self_report × 0.25) + (focus_variance × 0.25) + (schedule_irregularity × 0.25) + (impulse_spending × 0.25)
```

---

## Archetype Classification

Uses a 2-axis system: **Execution** vs **Growth**

```
                    GROWTH
                      ↑
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
    │   AT RISK       │ EMERGING        │
    │   (Low/Low)     │ TALENT          │
    │                 │ (Low/High)      │
    ├─────────────────┼─────────────────┤
    │   RELIABLE      │ COMPOUNDING     │
    │   OPERATOR      │ BUILDER         │
    │   (High/Low)    │ (High/High)     │
    └─────────────────┼─────────────────┘
                      │
                    EXECUTION →
```

### Thresholds (Exclusive Model)

| Archetype | Execution | Growth | Description |
|-----------|-----------|--------|-------------|
| **Compounding Builder** | ≥0.85 | ≥0.80 | Elite shipper + steep learning curve |
| **Reliable Operator** | ≥0.70 | <0.65 | Consistent but plateauing |
| **Emerging Talent** | <0.70 | ≥0.65 | Low output but rapid improvement |
| **At Risk** | <0.70 | <0.65 | Low completion, no improvement trend |

---

## Cross-Source Delta Analysis

**Key Innovation:** Measure dissonance between sources.

```
delta = |source_a - source_b|

High delta = potential coaching opportunity
```

### Deltas to Track

1. **Social vs AI Dissonance**
   - Social posts confidence vs AI conversation vulnerability
   - Large gap = performer vs authentic self

2. **Income Expectation Delta**
   - Claimed income vs actual income
   - Overestimation = potential disappointment

3. **Professional vs Private Dissonance**
   - Email energy vs Lifelog energy
   - Different personas in different contexts

---

## Source Weight Configuration

```python
SOURCE_WEIGHTS = {
    # (execution_weight, growth_weight, self_awareness_weight)
    "persona":       (0.10, 0.05, 0.10),
    "lifelog":       (0.20, 0.15, 0.25),
    "conversations": (0.10, 0.20, 0.25),  # AI convos = most honest
    "transactions":  (0.25, 0.15, 0.10),
    "emails":        (0.15, 0.10, 0.10),
    "calendar":      (0.10, 0.20, 0.05),
    "social_posts":  (0.10, 0.15, 0.15),
}
```

---

## Application Example: Theo Nakamura

Using this algorithm on Theo (23yo Austin designer):

| Dimension | Score | Interpretation |
|-----------|-------|----------------|
| **Execution** | ~0.45 | Mid-tier. 200 invoices sent, ~12.5% win rate. Shows up to shifts. |
| **Growth** | ~0.65 | Good. School of Motion ($200/mo), learning sessions visible. |
| **Self-Awareness** | ~0.70 | High. ADHD self-reported. Talks to AI about struggles. |
| **Financial Stress** | ~0.75 | High. $6k debt, spending ~90% of income. |
| **ADHD Indicator** | ~0.80 | High. Schedule irregularity + focus variance + self-report. |

### Delta Analysis:
- **Social (0.8 confidence) vs AI (0.4 confidence) = 40% dissonance**
- Significant gap between public brand and private doubt

---

## Research Context

Key academic papers in this space:

1. **"Twenty Years of Personality Computing"** (2025) — Fabio Celli et al. — Comprehensive review of the field

2. **"Personality Profiling: How informative are social media profiles?"** (2023) — Tests accuracy of predicting personal info from online profiles

3. **"Large Language Models Can Infer Psychological Dispositions of Social Media Users"** (2023) — Shows LLMs can predict personality from posting behavior

4. **"AI-enabled exploration of Instagram profiles predicts soft skills"** (2022) — Directly applies to hiring decisions

5. **Michal Kosinski's work** — Pioneered using digital footprints for personality prediction

---

## Implementation

See `profiler.py` for the complete Python implementation with:
- Signal computation functions
- Temperature-controlled normalization
- Delta analysis
- Archetype classification

---

## References

- Rewind Profiler Agent: https://github.com/Tar-ive/rewind/blob/main/backend/src/agents/profiler_agent.py
- Porthon Dataset: https://github.com/Tar-ive/porthon
