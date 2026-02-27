# Data Pattern Analysis — Theo Nakamura (p05)

## What You Have: 6 Signal Layers

| Source | Volume | Signal Type |
|--------|--------|-------------|
| `transactions.jsonl` | 120 entries, 20 months | **Behavioral reality** — what actually happens with money |
| `lifelog.jsonl` | 150 entries | **Inner narrative** — unfiltered thoughts, wins, rumination |
| `conversations.jsonl` | 8 sessions | **Unfiltered self** — most psychologically honest layer |
| `calendar.jsonl` | 80 events | **Time allocation** — what he actually commits to |
| `emails.jsonl` | 80 emails (44 sent / 36 recv) | **Professional relational self** |
| `social_posts.jsonl` | 50 posts | **Performed self** — curated, public-facing |

---

## Key Patterns Found

### 1. The Public/Private Dissonance (Most Valuable Signal)

A ~40% gap exists between public and private identity layers:

| Layer | Confidence Score | Evidence |
|-------|-----------------|----------|
| Social posts | `0.8` | "Raised my rate. Didn't die." / "ADHD is a superpower" |
| Lifelog | `0.5` | "paid the minimum. hate that I paid the minimum" |
| AI conversations | `0.4` | "I undercharged a client again. $600 for 40 hours" |

**Algorithm use:**
```
delta = |social_confidence - ai_confidence|
```
This delta is a **coaching opportunity score**. A person who projects confidence publicly but admits failure privately needs authenticity-focused recommendations, not more skill content.

---

### 2. Stated vs Behavioral Reality Gap

Three places where numbers don't match:

```
Claimed income:   $38,000/year
Actual tracked:   $36,400 over 20 months = ~$21,840/year annualized
Gap:              ~45% overestimation

Claimed goal:     "pay off $6k debt"
Actual behavior:  7 payments totaling $812 = minimum-only payments
                  Debt barely moving

Invoice win rate: 0.13 (200 invoices estimated → 26 won)
School of Motion: $200/month spend on skills
Bottleneck:       Conversion, NOT skills
```

**Algorithm use:** When `stated_goal ≠ behavioral_trajectory`, flag as a priority intervention point. The algorithm should recommend based on **actual behavior**, not stated goals.

---

### 3. ADHD Behavioral Fingerprint Across Sources

This shows up in 4 independent layers — strong confirmed signal:

```
Persona:      has_adhd = true (self-reported)
Lifelog tags: adhd (14), anxiety (12), productivity (20)
Transactions: skating gear bought multiple times (impulse)
              Repeated identical Veracruz tacos entries (routine, habitual)
Calendar:     "Tax prep attempt (2h) at coffee shop" → avoidance + environment hack
Lifelog text: Identical entries at 4:16am AND 8:22am same day → fragmented attention
Conversations: "I have ADHD and I'm struggling to finish projects"
```

**Algorithm use:** ADHD indicator as a **modifier** that shifts recommendation *style*, not just content. Shorter tasks, body-doubling suggestions, environment design — not more information to consume.

---

### 4. Tag Frequency = True Priority Map

From `lifelog_summary.json`:

```
freelance:    42  ← #1 concern (livelihood)
austin:       30  ← identity/belonging anxiety
milestone:    29  ← achievement-seeking
finances:     28  ← active stress
design:       24  ← craft identity
identity:     21  ← who am I becoming
productivity: 20  ← ADHD-driven struggle
```

From themes:
```
work_freelance:  60 entries
finances:        38 entries  ← second most
austin_life:     30
```

**Algorithm use:** Tag frequency becomes a `priority_vector`. Recommendations should be weighted to match — heavy on freelance + financial execution, not identity exploration.

---

### 5. Learning Investment vs Revenue Return (Mis-Allocation Signal)

```
School of Motion:  $200/month × 10+ months = $2,000+
Other learning:    $2,200 total
Total learning:    ~$4,200+

Invoice win rate:  0.13
Revenue avg:       $1,820/month (low for 20 months of effort)
```

He's investing heavily in *skills* but the bottleneck is *conversion*. This is the "wrong ladder against the wrong wall" pattern.

**Algorithm use:**
```
if learning_spend_ratio > conversion_rate_threshold:
    recommend(client_acquisition) > recommend(more_skills)
```

---

### 6. Financial Stress Triangulation

Three sources confirm the same stress — high-confidence signal:

```
Transactions: (subscriptions + rent) / total_revenue
              ($2,383 + $7,875) / $36,400 = 28% of total income
              Monthly: ~$1,820 avg revenue vs ~$1,800 estimated burn → breakeven or negative

Lifelog:      finances = 38/150 entries (25% of all logs mention money)
              Tags: debt (12), anxiety (12) — cluster together

Persona:      $6k credit card debt, variable income, explicit stated pain point
```

**Algorithm use:** Multi-source confirmation = high-confidence stress score. When 3+ sources confirm the same theme → amplify that signal in profile scoring.

---

## Algorithm Architecture

```
Input Data                 Computed Signals              Output
──────────                 ────────────────              ──────
transactions    ──────┐
lifelog         ───┐  │    execution_score   (~0.30)
conversations   ─┐ │  │    growth_score      (~0.65)
calendar        ─┤─┼──┼──► self_awareness    (~0.70)  → Archetype
emails          ─┤─┘  │    financial_stress  (~0.75)    + Recs
social_posts    ─┘     │    adhd_indicator    (~0.80)
persona         ───────┘

                        delta analysis
                        ──────────────
                        social vs AI         → coaching opportunity
                        stated vs actual     → reality check
                        learning vs convert  → reallocation signal
```

---

## Recommendation Logic

```python
if archetype == "emerging_talent":
    # High growth intent, low execution
    # Theo's case: knows what's wrong, can't execute it

    if financial_stress > 0.7:
        recommend("pricing_calculator_tool")             # Concrete, not motivational
        recommend("contract_template_with_revision_limits")
        recommend("debt_payoff_calculator")

    if learning_spend > revenue_conversion:
        recommend("client_acquisition_course")           # Not more design skills
        recommend("cold_outreach_templates")

    if adhd_indicator > 0.7:
        recommend("body_doubling_community")
        recommend("chunked_task_templates")              # Not long-form content
        recommend("invoice_automation_tool")             # Reduce admin friction

    if social_vs_ai_delta > 0.35:
        recommend("vulnerability_marketing_guide")       # Their gap is the content
        recommend("authentic_pricing_story_template")
```

---

## Three Highest-Leverage Features

1. **Cross-source delta** — gap between public/private self = exact coaching target
2. **Spend vs behavior misalignment** — learning spend vs conversion rate reveals wrong-ladder problem
3. **Multi-source tag clustering** — when `finances` appears in transactions + lifelog + AI conversations simultaneously, it's a confirmed high-priority signal, not noise

---

## Current Algorithm Blind Spots

These are gaps in the current data that `profiler.py` fills with estimates:

| Gap | What's Missing | Impact |
|-----|---------------|--------|
| Revenue trend | Month-by-month breakdown not parsed; only aggregate total | Can't compute trajectory direction |
| Email sentiment | 80 emails with no body content | Can't detect client relationship health |
| Calendar adherence | All 80 events typed as `"event"`, no completion status | Show-rate computed as estimate, not real |
| Impulse spend classification | No transaction categories beyond manual tags | ADHD impulse score is assumed, not measured |

---

## Archetype Verdict

Based on execution score (~0.30) and growth score (~0.65):

```
                    GROWTH
                      ↑
      ┌───────────────┼───────────────┐
      │               │  ★ EMERGING   │
      │   AT RISK     │    TALENT     │
      │               │  [THEO HERE]  │
      ├───────────────┼───────────────┤
      │   RELIABLE    │  COMPOUNDING  │
      │   OPERATOR    │    BUILDER    │
      └───────────────┼───────────────┘
                      │          EXECUTION →
```

**Emerging Talent** — High growth orientation, significant learning investment, self-awareness about problems, but execution (converting effort to revenue) is weak. The algorithm should prioritize removing friction from execution, not adding more learning inputs.
