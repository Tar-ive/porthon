# Questline — Project Requirements

## Overview

**Project Name:** Questline
**Track:** Track 2 — Deliver personal value through an AI agent
**Description:** Questline is an AI agent that analyzes your past behavioral data (financial, health, social, calendar) to project the most likely scenarios for your life in 1, 5, and 10 years. You select a scenario, and Questline gives you small, concrete actions you can take *today* to steer toward that future — grounded in Atomic Habits philosophy and cross-domain pattern recognition.

---

<Proposal name="Problem Statement & Use Case">

### Problem Statement

People generate behavioral data across 5+ platforms daily but never connect the dots. Financial apps show spending. Calendar apps show busyness. Health apps show steps. No tool synthesizes these signals into "here's where your life is heading" and "here's what to do today."

### Use Case

Questline is a **behavioral futures engine** — it ingests your digital footprint, computes a quantitative behavioral profile (execution, growth, self-awareness, financial stress, ADHD indicators), projects 3 divergent life scenarios, and generates grounded daily micro-actions for the path you choose.

### Always-On Companion Agent

Questline is not a tool you open, use, and close. It is an **always-on, proactive companion agent** that continuously monitors your behavioral signals, detects shifts in trajectory, and surfaces timely nudges before you ask. The Oracle doesn't wait for queries — it notices when your spending pattern diverges from your savings goal, when your calendar density is approaching burnout thresholds, or when a new skill cluster is emerging from your hyperfocus episodes. It reaches out with grounded, scenario-aware micro-actions at the moment they're most actionable.

</Proposal>

---

## Data Story

- **Who owns the data?** The user. All data is synthetic (provided by hackathon organizers) representing a real person's behavioral footprint.
- **Where does it come from?** Five structured data sources per persona: financial transactions (tagged by category), lifelog reflections (free-text journal entries), calendar events (with cross-refs to emails), social posts, and a persona profile.
- **How is consent handled?** Users see a consent screen showing exactly which data categories are being analyzed and can toggle sources on/off before any processing begins. The consent.json schema from the hackathon dataset is surfaced directly in the UI so judges can see data governance is real, not cosmetic.
- **Why is this valuable?** Most people never connect the dots across their own behavioral domains. Questline surfaces non-obvious cross-domain patterns and translates them into one actionable step today — not vague life advice.

---

## Core Architecture

```
┌──────────────────────────┐
│   Persona Data Sources    │
│  transactions.jsonl       │  tagged financial events
│  lifelog.jsonl            │  free-text reflections & activities
│  calendar.jsonl           │  events with cross-refs
│  social_posts.jsonl       │  sentiment + topic signals
│  persona_profile.json     │  goals, pain points, personality
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│     Consent Layer         │  User toggles data sources on/off
│  (consent.json schema)    │  No processing until confirmed
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│   Behavioral Profiler     │  PROFILING_MATH scoring framework
│   (Step 0 — deterministic) │  5 dimensional scores + archetype
│                           │  Feeds into Pattern Analyzer + Scenarios
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│   Structured Extractor    │  Parse jsonl → typed time-series structs
│   (deterministic code)    │  Spending by category/week, activity
│                           │  frequency, calendar density, social
│                           │  sentiment score by week
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│   Pattern Analyzer        │  Claude tool-use step with structured
│   (Agent Step 1)          │  JSON input — not raw text dumps.
│                           │  Outputs typed PatternReport:
│                           │  { trend, domain, correlation,
│                           │    confidence, supporting_data_refs }
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│   Scenario Generator      │  Takes PatternReport + persona goals.
│   (Agent Step 2)          │  Outputs 3 Scenario objects:
│                           │  { title, narrative, timeframe,
│                           │    likelihood, pattern_refs[] }
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│   Action Planner          │  Takes selected Scenario + live
│   (Agent Step 3)          │  calendar/transaction data.
│                           │  Outputs ActionPlan:
│                           │  { action, rationale, data_ref,
│                           │    compound_effect_summary }
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│      Frontend UI          │  Consent → Stats → Scenarios → Actions
└──────────────────────────┘
```

<Proposal name="Step 0: Behavioral Profiler (PROFILING_MATH.md)">

#### Step 0: Behavioral Profiler

Before the Pattern Analyzer runs, a deterministic **Behavioral Profiler** computes a quantitative baseline using the PROFILING_MATH.md scoring framework:

- **5 Dimensional Scores:** Execution (task completion velocity × consistency), Growth (new skill acquisition + challenge-seeking), Self-Awareness (reflection depth × behavioral adjustment rate), Financial Stress (burn rate vs. savings trajectory), ADHD Indicator (context-switching frequency × incomplete task ratio)
- **Scoring method:** Exponential decay weighting (recent data matters more) + sigmoid normalization to 1–10 scale
- **Archetype classification:** Compounding Builder / Reliable Operator / Emerging Talent / At Risk — derived from score vector clustering
- **Cross-source deltas:** Compares self-reported data (lifelog) vs. behavioral data (transactions, calendar) to compute authenticity gaps
- **Output feeds into:** Pattern Analyzer (as quantitative priors), Scenario Generator (as baseline for projection), and Stats Dashboard (US-2.3 renders these scores directly — they're computed, not LLM-generated)

</Proposal>

**Key architectural principle:** Each agent step receives structured typed data (not raw text). The LLM interprets patterns and generates narrative — it does not parse raw files. This is what separates a real pipeline from an API wrapper and is the primary Completeness signal for judges.

---

## Cross-Domain Insight Targets

These are the specific second-order insights the pipeline must be capable of surfacing. They are grounded in the actual data shape available (transactions tagged by category, lifelog with work/health/relationship tags, calendar density, social post sentiment).

| Insight | Domains crossed | Why it's non-obvious |
|---------|----------------|----------------------|
| Social spending spikes in weeks following high-density meeting calendars | calendar + transactions | Captures stress-relief spending pattern |
| Lifelog anxiety tags correlate with reduced exercise frequency the following week | lifelog + lifelog activity | Captures anxiety → inactivity feedback loop |
| Relationship-tagged lifelog entries decrease during promotion-push calendar periods | calendar + lifelog | Captures career ambition cost on relationships |
| Social post sentiment drops 10–14 days after sustained high-meeting-density periods | calendar + social | Leading burnout indicator |
| Discretionary spending (dining/social) inversely tracks health activity frequency | transactions + lifelog | Captures substitution behavior |

The pipeline must produce at least **two** cross-domain insights per persona. Single-domain trends are supporting context only.

---

## Typed Data Contracts

Each pipeline stage passes a typed struct. These are defined in code, not ad-hoc.

```python
# Step 1 output
PatternReport = {
  "patterns": [
    {
      "id": "p_001",
      "trend": str,           # e.g. "Social spending +18% in high-meeting weeks"
      "domains": list[str],   # e.g. ["calendar", "transactions"]
      "confidence": float,    # 0.0–1.0
      "data_refs": list[str], # e.g. ["cal_0001", "t_0004"]
      "is_cross_domain": bool
    }
  ]
}

# Step 2 output
ScenarioSet = {
  "scenarios": [
    {
      "id": "s_001",
      "title": str,
      "narrative": str,
      "timeframe": "1yr" | "5yr" | "10yr",
      "likelihood": "most_likely" | "possible" | "aspirational",
      "pattern_refs": list[str],  # must reference PatternReport ids
      "goal_alignment": list[str] # references persona_profile goals
    }
  ]
}

# Step 3 output
ActionPlan = {
  "scenario_id": str,
  "actions": [
    {
      "action": str,          # specific and time-bound
      "rationale": str,       # 1-2 sentences linking to pattern + scenario
      "data_ref": str,        # specific record that justifies this action
      "compound_summary": str # how this compounds toward the scenario
    }
  ]
}
```

---

## User Stories

### Epic 1: Data Consent & Loading

**US-1.1 — View available data sources**
As a user, I want to see which categories of my data are available (financial, health, calendar, social) so that I understand what the system will analyze.
- **Acceptance Criteria:** Consent screen lists each data category with a brief description and a toggle. No processing occurs until the user confirms.

**US-1.2 — Toggle data sources**
As a user, I want to enable or disable specific data categories before analysis so that I control what the system sees.
- **Acceptance Criteria:** Toggling a source off excludes it entirely from the pipeline. At least one source must be enabled to proceed.

**US-1.3 — Confirm and proceed**
As a user, I want to explicitly confirm my data selections before the agent starts processing so that nothing happens without my consent.
- **Acceptance Criteria:** A "Start Analysis" button is disabled until at least one source is selected. Clicking it triggers the pipeline and shows a loading/progress state.

---

### Epic 2: Pattern Analysis

**US-2.1 — See my behavioral patterns**
As a user, I want the system to surface key trends and patterns from my data so that I understand where I currently stand.
- **Acceptance Criteria:** The system displays 3–7 key patterns derived from PatternReport structs. Each cites the specific data records that support it (data_refs visible on hover/expand).

**US-2.2 — See cross-domain correlations**
As a user, I want the system to identify connections *between* data categories so that I get insights I couldn't see on my own.
- **Acceptance Criteria:** At least two displayed patterns are `is_cross_domain: true`. Cross-domain insights are visually distinguished (different color/badge). Single-domain trends are shown as supporting context only.

**US-2.3 — View my character stats**
As a user, I want to see a summary of my current "stats" (financial health, physical activity, social engagement, career momentum, relationship quality) so that I get an at-a-glance picture of my life.
- **Acceptance Criteria:** Stats are derived from actual data computations, not hardcoded. Each stat has a score (1–10) and a one-line explanation of how it was calculated from the data.

---

### Epic 3: Scenario Projection

**US-3.1 — See projected future scenarios**
As a user, I want the system to generate 3 plausible future scenarios based on my current patterns so that I can see where my trajectory is heading.
- **Acceptance Criteria:** Each scenario explicitly references 2+ PatternReport pattern_ids. Scenario narratives are grounded in the persona's stated goals (goal_alignment populated). Scenarios represent meaningfully different outcomes.

**US-3.2 — Understand scenario likelihood**
As a user, I want each scenario to show a relative likelihood so that I can gauge which future is most probable.
- **Acceptance Criteria:** Each scenario displays likelihood label (Most Likely / Possible / Aspirational) derived from pattern confidence scores, not hardcoded.

**US-3.3 — Select a target scenario**
As a user, I want to select a scenario as my target future so that the system can plan actions to move me toward it.
- **Acceptance Criteria:** Selecting a scenario triggers Action Planner with the scenario_id. Only one scenario selectable at a time.

---

<Proposal name="Conversational Agent in Scenario Flow">

#### Proposed: Scenario-Aware Conversational Agent

After scenario selection, the chat agent (Oracle) should receive the full pipeline context and act as a grounded companion:

- **Full context injection** — the Oracle receives the behavioral profile scores (Step 0), detected patterns (Step 1), and the selected scenario (Step 2) as structured context, not just the scenario title
- **SOUL.md personality** — responds as a companion who "knows" the user, using the personality framework already built (warmth, directness, pattern-referencing)
- **Intent-routed responses** — the existing intent classifier (factual / pattern / advice / reflection / emotional) routes queries to different response strategies, each grounded in the pipeline data
- **Optional KG retrieval** — when LightRAG is configured, queries are enriched with cross-domain context from the knowledge graph, enabling the Oracle to surface connections the user hasn't explicitly asked about
- **Scenario grounding** — every response naturally references the selected scenario's trajectory, helping the user internalize the path they've chosen

</Proposal>

### Epic 4: Action Planning

**US-4.1 — Get today's micro-actions**
As a user, I want to receive 3–5 small, concrete actions I can take *today* to move toward my selected scenario.
- **Acceptance Criteria:** Actions are specific and time-bound (e.g., "Block 6–6:20pm for a walk — your calendar is free tonight"). Each action includes a data_ref to the specific record that justifies it. Generic actions ("exercise more") are a test failure.

**US-4.2 — Understand why each action matters**
As a user, I want each action to include a brief explanation linking it to my selected scenario.
- **Acceptance Criteria:** Each action has a rationale field (1–2 sentences) that references a specific detected pattern and connects it to the chosen scenario's outcome.

**US-4.3 — See the compound effect**
As a user, I want to understand how these daily actions accumulate toward the scenario.
- **Acceptance Criteria:** A compound_summary is displayed per action. A summary section shows projected stat movement (e.g., "Consistent 20-min walks shift your activity score from 3/10 → 6/10 in 6 months — the foundation of Scenario A").

---

### Epic 5: UI & Experience

**US-5.1 — Complete the full loop in under 60 seconds**
As a user, I want to go from app launch to seeing my today-actions in under a minute.
- **Acceptance Criteria:** Consent → Patterns → Scenarios → Actions completable in 4 screens. Each agent step streams output progressively so the UI never appears frozen. Total wall-clock time from "Start Analysis" to final actions screen ≤ 60 seconds for the Jordan persona.

**US-5.2 — Non-developer usability**
As a non-technical user, I want the interface to be intuitive with no jargon.
- **Acceptance Criteria:** No technical terms, data_refs, or raw JSON visible in default view. Data refs visible only on expand/hover for judges who want to verify grounding.

**US-5.3 — RPG-style presentation (stretch)**
As a user, I want my stats and scenarios presented with an RPG aesthetic so that engaging with my data feels compelling rather than clinical.
- **Acceptance Criteria:** Stats render as RPG-style attributes with levels/bars. Scenarios render as branching paths on a visual timeline. This is a stretch goal — ship P0/P1 first.

---

## Build Priority

| Priority | Item | Scoring Impact |
|----------|------|----------------|
| P0 | Structured Extractor — parse jsonl into typed time-series | Completeness (50 pts) |
| P0 | 3-step agent pipeline with typed contracts between steps | Completeness (50 pts) |
| P0 | Streaming UI — show real-time agent progress during live LLM calls | Completeness (50 pts) |
| P1 | Consent screen with source toggles wired to pipeline | Track Criteria (25 pts) |
| P1 | At least 2 cross-domain insights surfaced per persona | Innovation (15 pts) |
| P1 | Data refs visible on expand (judges can verify grounding) | Completeness + Innovation |
| P1 | Clean 4-screen UI with plain-language output | UX (10 pts) |
| P2 | Character stats dashboard (derived from data, not hardcoded) | Innovation + UX |
| P2 | Compound effect summary per action | Track Criteria + UX |
| P3 | RPG map visualization | UX polish (stretch) |

---

## Demo Strategy

The demo uses **live LLM calls** — this is a feature, not a risk. Judges watching the agent think in real time is a stronger completeness signal than a pre-baked result. The demo persona is **Jordan Lee (p01)** — her goals (Director promotion, half marathon, house savings, relationship) produce the most emotionally resonant scenarios.

**Demo script target:**
1. Consent screen — toggle off one source live to show it works
2. Start Analysis — streaming progress visible per agent step ("Extracting patterns… Generating scenarios…")
3. Pattern screen — call out one cross-domain insight explicitly ("Notice this one crosses two domains")
4. Scenario screen — select "Aspirational" scenario
5. Actions screen — point to one action and trace it back to a specific data record

**Reliability requirements for live calls:**
- Each agent step must have a **30-second timeout** with a graceful error state (not a crash)
- Show a **streaming progress indicator** during each step — blank screens while waiting are a judge confidence-killer
- Pre-minimize input token count: the Structured Extractor must summarize raw jsonl into compact JSON before passing to the LLM. Jordan's full dataset should not exceed ~8k tokens of LLM input per step.
- **Warm the API connection** before the demo starts (one throwaway call in the background on app load)
- Have a **single-keypress fallback** (e.g., `?` key in dev mode) that loads a pre-computed result only if a step genuinely fails mid-demo. This fallback should never be needed but must exist.

---

## Tech Stack

- **Frontend:** React (single-page app)
- **Agent Backend:** Python — multi-step Claude API chain with tool use; structured JSON in/out at each step
- **Data Layer:** Hackathon-provided jsonl/json per persona, parsed by deterministic Structured Extractor before any LLM call
- **Deployment:** TBD (Vercel/Railway/local demo)

<Proposal name="Pydantic Deep Agents as Agentic Framework">

#### Proposed: pydantic-deep as Agent Execution Framework

Replace raw OpenAI/Claude API calls with `pydantic-deep` agents, modeled after `apps/deepresearch`:

- **`create_deep_agent()` factory** — each pipeline step becomes a typed agent with Pydantic `output_type` enforcing data contracts (PatternReport, ScenarioSet, ActionPlan). No JSON parsing failures.
- **Subagent delegation** — parallel pattern analysis across data domains (e.g., a financial sub-agent and a calendar sub-agent running concurrently, results merged by a coordinator agent)
- **Structured output guarantees** — Pydantic validation at every agent boundary. If an agent returns malformed data, it retries with the validation error as feedback.
- **Middleware stack** — audit logging, token budget enforcement (hard cap per step), timeout handling (30s per step as specified)
- **Skills system** — SOUL.md and USER.md become skill files injected into agent context, replacing manual prompt concatenation
- **Chat Oracle as deep agent** — the conversational agent gets memory, context compression, and checkpoint support via the framework's built-in session management
- **WebSocket streaming** — replaces SSE for richer real-time UI (binary frames, connection multiplexing, bidirectional communication for mid-stream user interrupts)

</Proposal>

---

<Proposal name="Always-On Proactive Companion Agent">

### Proposed: Questline as Always-On Behavioral Companion

Questline is not a tool you open, use, and close. It is an **always-on, proactive companion agent** — a behavioral futures engine that continuously monitors your data signals, detects trajectory shifts, and surfaces timely nudges before you ask.

The Oracle doesn't wait for queries. It notices when your spending pattern diverges from your savings goal, when your calendar density approaches burnout thresholds, or when a new skill cluster is emerging from your engagement patterns. It reaches out with grounded, scenario-aware micro-actions at the moment they're most actionable.

</Proposal>

<Proposal name="Neurodiverse-Aware Behavioral Intelligence">

### Proposed: ADHD-Optimized Pattern Engine

Traditional productivity tools penalize context-switching and label interest pivots as "quitting." Questline reframes neurodivergent behavioral patterns as signal, not noise — and feeds them into scenario generation for ultra-realistic life projections.

#### Hyperfocus Detection & Skill Convergence

The behavioral profiler detects hyperfocus episodes from chat data, calendar density, and activity logs — capturing depth + duration rather than mere frequency:

| ADHD Brain | What Questline Does |
|---|---|
| Hyperfocus on Python for 3 weeks, then pivots to Blender 3D, then back to Python + ML | Captures each as a **skill cluster** with depth score, not "abandoned interest" |
| Apparent "quitting" pattern | Maps as **convergence trajectory**: "3D + ML = spatial computing" |
| No idea what job fits | Matches convergence to market demand: "Unity ML, AR/VR roles paying $140k" |
| Overwhelmed by long-term goals | Generates **micro-milestone learning paths** calibrated to hyperfocus cycle length |

#### Pipeline Stages

1. **Decontextualization** — resolves references from conversation history into standalone skill/interest signals so the profiler doesn't lose context across hyperfocus pivots
2. **Hyperfocus Detection** — classifies whether the user is in a depth episode (sustained single-domain engagement, reduced context-switching, extended sessions). During hyperfocus the agent avoids interrupting; after, it consolidates what was learned
3. **Memory Extraction** — extracts skills, interests, and engagement patterns as typed skill nodes in the knowledge graph, enabling convergence detection across time
4. **Skill Cluster Mapping** — groups apparently unrelated interests into convergence clusters using semantic similarity + temporal co-occurrence. Surfaces non-obvious career/project paths
5. **Accelerated Depth Domains** — identifies domains where the user achieves mastery faster than baseline (high depth score / low time). These become priority inputs for scenario generation

#### Simulation Grounding

The ADHD behavioral data (hyperfocus cycles, skill clusters, convergence trajectories, accelerated depth domains) feeds directly into the Scenario Generator as high-signal priors. Scenarios account for non-linear skill acquisition, predict which convergence paths have highest market value, and calibrate action plans to the user's actual attention patterns rather than neurotypical assumptions. This makes 1/5/10yr projections ultra-realistic for neurodiverse users.

#### Monetization Path (Stretch)

- Micro-rewards via x402 stablecoin payments for completing micro-milestones
- Platform-assisted job matching from convergence clusters → percentage of signing bonus on successful placement

</Proposal>

---

## Known Risks

1. **Scope creep** — RPG visualization and values alignment are explicitly deferred. Ship P0 and P1 first.
2. **API wrapper perception** — Mitigated by typed contracts: judges can be shown that LLM input is structured JSON, not raw file dumps.
3. **Demo reliability** — Mitigated by streaming UI, per-step timeouts with graceful error states, minimized input token counts, and a hidden single-keypress fallback for catastrophic failure only.
4. **Cross-domain insight depth** — The five specific insight targets above are the quality bar. If the pipeline can't surface at least two of them for Jordan, the scenario generation will read as generic.
5. **Scenario/action quality drift** — Validate outputs against Jordan's persona_profile.json goals. Every scenario should map to at least one stated goal. Every action should reference a specific data record.
