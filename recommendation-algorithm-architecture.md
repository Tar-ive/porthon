# Recommendation Algorithm Architecture
## Profiler Enhancement — Truly Personal Recommendations

**Date:** 2026-02-27
**Status:** Draft - General Purpose for Tiktok Like Algorithms, still not completely useful for Us and our Usecase but good reading materials 
**Author:** Architecture Review

---

## 1. The Core Problem

Most recommendation systems feel generic because they treat the user as a *cluster member*, not an *individual*. They ask: "what do people like you like?" The goal here is different — to ask "what does *this person*, in *this moment*, in *this context*, actually want?"

This requires three things working together:
1. A rich, multi-signal profiler that captures *behavioral fingerprints*, not just categories
2. A recommendation engine that weights recency, context, and drift over time
3. A feedback loop that continuously corrects itself

---

## 2. Requirements

### Functional
- Build and maintain a living user profile from behavioral signals
- Generate ranked candidate recommendations in real time
- Adjust to changing tastes over time (handle concept drift)
- Support cold-start for new users with minimal data
- Explain why a recommendation was made (transparency)

### Non-Functional
- Recommendation latency: < 100ms at the serving layer
- Profile update latency: near-real-time (< 5 seconds from signal to profile)
- Scale: designed to grow from hundreds to millions of users without re-architecture
- Privacy-first: signals stored with user consent; profiles deletable

### Constraints
- Must integrate with existing profiler codebase
- Should be incrementally deployable — not a big-bang rewrite

---

## 3. Signal Taxonomy: The Heart of True Personalization

This is the most important section. Signals fall into six families:

### 3.1 Explicit Signals (High confidence, Low volume)
These are the user *telling* you something directly.

| Signal | What it reveals |
|--------|----------------|
| Explicit ratings (stars, thumbs) | Strong directional preference |
| "Save for later" / Bookmarks | Intent and interest, not just engagement |
| "Not interested" / Dismissal | Negative space — as important as positives |
| Follows / Subscribes | Sustained, active relationship with a topic or creator |
| Sharing to others | High-confidence endorsement; signals identity too |
| Manual preference settings | Ground truth about stated preferences |

**Enhancement note for profiler:** Explicit signals should be stored with full context — *when* the user rated, *what session* they were in, *what they looked at before*. A 5-star rating given after a long session of exploration means something different than one given immediately.

---

### 3.2 Implicit Behavioral Signals (Medium confidence, High volume)
The user is *showing* you something without saying it.

| Signal | What it reveals | Trap to avoid |
|--------|----------------|---------------|
| Dwell time / Time on page | Genuine interest | Long time can mean confusion too |
| Scroll depth | How far they really read | Autoplay can inflate this |
| Return visits to same item | Strong interest signal | Distinguish from accidental |
| Re-reads / Re-listens | Deep engagement | |
| Copy-paste events | Utility / research mode vs. enjoyment mode | |
| Hover time on thumbnails | Decision consideration | |
| Search query reformulations | What they couldn't find; latent needs | |
| Click-through from recommendation | Validation of rec quality | |
| Abandonment patterns | What turned them off | |

**Key insight:** The *ratio* of these signals matters more than absolutes. Someone who reads 80% of every article is different from someone who spikes to 100% on one topic. The profiler should track distribution shapes, not just averages.

---

### 3.3 Contextual Signals (Multipliers on other signals)
The same person wants different things in different contexts. This is what most systems miss.

| Signal | Why it matters |
|--------|---------------|
| **Time of day** | Morning = quick headlines; late night = long reads or entertainment |
| **Day of week** | Weekday commute vs. Sunday deep-dive |
| **Device type** | Mobile = snackable; desktop = research mode |
| **Session length so far** | Short session = high-value only; long session = explore |
| **Entry point** | Came from search vs. opened app directly vs. notification |
| **Network type** | Slow connection → prefer lightweight content |
| **Geographic context** | Local events, regional relevance (with privacy sensitivity) |
| **Calendar context** | Season, holidays, major events in user's world |
| **Ambient context** | If available: is background noise high (commuting)? |

**Architecture implication:** Context should be a *real-time modifier* applied at serving time, not baked into the static profile. This means the recommendation score for any item = `base_score × context_multiplier`.

---

### 3.4 Sequential and Session Signals (Pattern-level intelligence)
What came before matters as much as what is being consumed now.

| Signal | What it reveals |
|--------|----------------|
| Within-session sequence | Current mood, rabbit-hole direction |
| Cross-session sequences | Ritualistic habits (e.g., always reads X then Y on Monday mornings) |
| Topic evolution within session | Going broad → narrow (researching) or narrow → broad (exploring) |
| "Completion then pivot" patterns | Satiation on a topic — time to shift |
| Re-entry after break | If they come back to finish something, it matters to them |

**Algorithm implication:** Use a session-level LSTM or Transformer encoder (small, fast) to encode the current session state and bias recommendations toward session momentum vs. session completion.

---

### 3.5 Social and Relational Signals (Identity as signal)
Not "what do people like you like" but "what does your specific social graph suggest?"

| Signal | What it reveals | Caution |
|--------|----------------|---------|
| Items shared *to* user by trusted people | High-quality signal about social relevance | Don't over-weight to avoid filter bubbles |
| What people the user follows engage with | Peripheral interest signal | Noisy without trust weighting |
| Collaborative filtering on tight social cluster | What close peers like | Distinguish close ties vs. weak ties |
| Comments and discussions entered | Deep engagement and opinion-formation | |

**Privacy note:** Social signals require explicit opt-in and should use privacy-preserving techniques (local computation, differential privacy on aggregates).

---

### 3.6 Negative Signals (The most underused signals)
What a user *doesn't* engage with defines them as precisely as what they do.

| Signal | What it reveals |
|--------|----------------|
| Skip within first 10 seconds | Immediate rejection |
| Scroll-past without hover | Category/format aversion |
| Explicit "not interested" | Hard exclusion |
| Repeated dismissal of same source | Source-level block, not just content |
| High open rate but zero completion | Title bait — user feels deceived (penalize source) |
| Notification open but immediate app close | Wrong timing, not wrong content |

**Enhancement note:** Negative signals should decay differently than positive ones. A single "not interested" click should have outsized weight in the short term but fade unless reinforced.

---

### 3.7 Temporal and Drift Signals (The person they're becoming)
People change. A recommendation system that treats you as who you were 6 months ago will feel out of touch.

| Signal | What it reveals |
|--------|----------------|
| Topic interest velocity | Rising vs. declining interest in a domain |
| Format preference shifts | Moved from articles to podcasts |
| Depth preference changes | Used to love summaries; now wants long reads |
| Vocabulary evolution in searches | Beginner → intermediate → expert trajectory |
| Session time changes | Life event affecting available time |

**Architecture implication:** Profiles should have a *recency-weighted decay* on all interest vectors. Use exponential decay with a tunable half-life per signal type (explicit signals decay slower; implicit signals decay faster).

---

## 4. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT / APP LAYER                        │
│   (Signal emission: clicks, hovers, scrolls, time, context)     │
└──────────────────────────────┬──────────────────────────────────┘
                               │ Event stream
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SIGNAL INGESTION LAYER                      │
│  ┌────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │  Event Queue   │  │  Signal Validator │  │ Context Enricher│  │
│  │  (Kafka/SQS)   │  │  (schema + rules) │  │ (device, time,  │  │
│  └───────┬────────┘  └──────────────────┘  │  location, etc) │  │
│          │                                  └─────────────────┘  │
└──────────┼──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PROFILE COMPUTATION LAYER                     │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │               FEATURE ENGINEERING PIPELINE               │    │
│  │  - Signal aggregation (raw → features)                   │    │
│  │  - Decay functions applied to signal families            │    │
│  │  - Sequence encoding (session LSTM/Transformer)          │    │
│  │  - Interest vector construction                          │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │                                    │
│  ┌──────────────────────────▼──────────────────────────────┐    │
│  │                  USER PROFILE STORE                      │    │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  │    │
│  │  │  Long-Term   │  │  Short-Term   │  │   Context    │  │    │
│  │  │  Profile     │  │  Session      │  │   Profile    │  │    │
│  │  │  (Redis +    │  │  State        │  │  (Real-time) │  │    │
│  │  │  Postgres)   │  │  (In-memory)  │  │              │  │    │
│  │  └──────────────┘  └───────────────┘  └──────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   RECOMMENDATION ENGINE                          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  CANDIDATE GENERATION (Recall stage)                    │    │
│  │  - Embedding similarity (ANN search via FAISS/Pinecone) │    │
│  │  - Collaborative filtering shortlist                    │    │
│  │  - Trending + editorial boosted pool                    │    │
│  │  - Diversity-injected candidates                        │    │
│  │  Output: ~500-1000 candidates                           │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │                                    │
│  ┌──────────────────────────▼──────────────────────────────┐    │
│  │  RANKING MODEL (Precision stage)                        │    │
│  │  - Feature: user profile vector × item features        │    │
│  │  - Feature: context multipliers                        │    │
│  │  - Feature: session state encoding                     │    │
│  │  - Feature: freshness + source quality score           │    │
│  │  - Feature: diversity penalty (already-shown topics)   │    │
│  │  Model: LightGBM or two-tower neural (depending on     │    │
│  │          latency budget)                               │    │
│  │  Output: scored + ranked list                          │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │                                    │
│  ┌──────────────────────────▼──────────────────────────────┐    │
│  │  POST-RANKING FILTERS                                   │    │
│  │  - Hard negatives applied (explicit "not interested")  │    │
│  │  - Already-seen filter                                 │    │
│  │  - Diversity enforcement (no topic monopoly)           │    │
│  │  - Serendipity injection (exploration budget: ~10%)    │    │
│  └──────────────────────────┬──────────────────────────────┘    │
└──────────────────────────────┼──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        SERVING LAYER                             │
│  - Pre-computed recommendation cache (warmed on profile update)  │
│  - Real-time context injection at serve time                     │
│  - A/B experiment allocation                                     │
│  - Explanation generation ("Because you read X...")             │
│  - < 100ms p99 latency target                                   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
                        USER SEES RESULTS
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FEEDBACK LOOP                                │
│  Outcome signals → back to Signal Ingestion Layer               │
│  Model retraining triggered by drift detection                  │
│  Offline evaluation: NDCG, diversity, serendipity metrics       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Data Model — The User Profile

```
UserProfile {
  user_id: UUID

  // Long-term interest vectors (decays slowly)
  interest_vectors: {
    topic_id -> {
      score: float,           // 0.0 - 1.0
      velocity: float,        // rising / falling / stable
      last_reinforced: timestamp,
      half_life_days: int,    // per-topic decay rate
      signal_sources: [explicit|implicit|social]
    }
  }

  // Format preferences
  format_affinity: {
    article: float, video: float, podcast: float,
    short_form: float, long_form: float, interactive: float
  }

  // Depth preference per topic
  depth_by_topic: {
    topic_id -> {beginner|intermediate|expert}
  }

  // Negative space
  hard_exclusions: [topic_id | source_id]
  soft_suppressions: {topic_id -> suppression_score}

  // Temporal patterns
  active_windows: [
    { day_of_week, hour_start, hour_end, session_type }
  ]

  // Creator/source relationships
  followed_sources: [{source_id, trust_weight}]
  blocked_sources: [source_id]

  // Session state (ephemeral, in-memory)
  current_session: {
    session_start: timestamp,
    items_consumed: [item_id],
    current_topic_sequence: [topic_id],
    satiation_scores: {topic_id -> float},
    session_intent: {explore|consume|research|casual}
  }

  // Profile metadata
  account_age_days: int,
  data_richness_score: float,  // 0.0 = cold start, 1.0 = fully warm
  last_updated: timestamp
}
```

---

## 6. Cold Start Strategy

New users have no signal. Handle in three phases:

**Phase 1: Onboarding (0-5 interactions)**
Explicit preference elicitation — ask a few questions framed as "What are you here for?" Pick 3-5 seed interests. Use these as starting topic vectors with moderate confidence.

**Phase 2: Rapid Learning (5-50 interactions)**
Weight implicit signals heavily. Use demographic-adjacent collaborative filtering (users who onboarded similarly). Widen exploration budget to 30% (vs. 10% at maturity) to gather signal faster. Show confidence intervals on recommendations visibly.

**Phase 3: Profile Maturity (50+ interactions)**
Transition fully to individual profile. Reduce exploration budget. Personalize signal decay rates based on observed behavioral consistency.

---

## 7. The Serendipity Budget — Fighting Filter Bubbles

A truly personal recommendation system must also surprise the user. Without intentional serendipity, the system converges into a filter bubble — showing only what it's already confident about, which eventually feels repetitive and stale.

**Implementation:**
- Reserve 10% of recommendation slots for "adjacent exploration" — items adjacent to known interests but not yet confirmed
- Reserve 2% for "wild card" — genuinely novel, high-quality items outside known interest graph
- Track serendipity engagement rate — if users engage with wild cards, expand the budget

This is the difference between a system that *reflects* the user back at themselves and one that *grows* with them.

---

## 8. Profiler Code Integration Points

For a developer enhancing an existing profiler, the key integration points are:

### 8.1 Signal Emission (Client side)
Instrument the client to emit structured events:
```json
{
  "event_type": "content_dwell",
  "user_id": "...",
  "item_id": "...",
  "session_id": "...",
  "duration_ms": 47200,
  "scroll_depth_pct": 78,
  "context": {
    "device": "mobile",
    "hour_of_day": 21,
    "day_of_week": "sunday",
    "network": "wifi",
    "entry_point": "push_notification"
  },
  "timestamp": "2026-02-27T21:14:00Z"
}
```

### 8.2 Profile Update API (Profiler core)
```
POST /profile/{user_id}/signals
  - Accepts batch of signal events
  - Returns updated profile delta (for debugging)
  - Triggers async recomputation if needed

GET /profile/{user_id}
  - Returns current profile with confidence scores
  - Supports partial views (e.g., ?view=interests_only)

DELETE /profile/{user_id}
  - Full erasure for privacy compliance
```

### 8.3 Recommendation Query API (Serving layer)
```
POST /recommend
  Body: {
    user_id: "...",
    context: { ... },        // real-time context
    session_state: { ... },  // current session
    n: 20,                   // candidates requested
    explain: true            // include explanation
  }
  Response: {
    recommendations: [
      { item_id, score, explanation, exploration_flag }
    ],
    profile_confidence: 0.82
  }
```

---

## 9. Trade-offs

| Decision | Option A | Option B | Chosen | Rationale |
|----------|----------|----------|--------|-----------|
| Profile storage | Single DB | Split hot/cold | Split | Short-term session state in memory; long-term in Postgres |
| Ranking model | Two-tower neural | LightGBM | LightGBM first | Faster to iterate; neural when data volume justifies |
| Signal decay | Fixed half-life | Per-signal adaptive | Adaptive | Explicit signals should persist longer than implicit |
| Serendipity | None | Fixed budget | Fixed 10-12% budget | Prevents filter bubbles without destabilizing experience |
| Explanation | None | Full | Lightweight | "Because you read X" increases trust without complexity |
| Cold start | CF only | CF + onboarding | Hybrid | Onboarding buys early signal that CF alone can't |

---

## 10. Metrics — How to Know It's Working

### Engagement Quality (not just quantity)
- **Completion rate** — did they finish what was recommended?
- **Return rate** — did they come back for more after this session?
- **Satisfaction signal rate** — saves, shares, explicit positive signals per session

### Personalization Health
- **Coverage** — what % of the catalog gets recommended (diversity check)
- **Serendipity engagement rate** — are users engaging with the exploration budget?
- **Profile drift delta** — is the profile actually evolving, or stuck?
- **Cold-to-warm transition time** — how quickly does the system learn new users?

### Anti-metrics (watch for these going wrong)
- Rising "not interested" dismissal rate → recommendations drifting
- Topic monopoly concentration → filter bubble forming
- Session shortening over time → user losing confidence in recommendations

---

## 11. What to Build Next (In Order)

1. **Signal instrumentation** — without rich signals, nothing else works. Start here.
2. **Profile store with decay** — get the data model right before adding models
3. **Simple candidate generation** — embedding similarity to get baseline quality up
4. **Context injection at serve time** — cheap, high-impact personalization
5. **LightGBM ranker** — add the ranking model once you have labeled impression data
6. **Serendipity budget** — add exploration once the core loop is working
7. **Drift detection + retraining pipeline** — keep it fresh automatically

---

*Every recommendation system reflects a philosophy about the user. Build one that says: "I see you as you actually are, not as a cluster label — and I'm paying attention to how you're changing."*
