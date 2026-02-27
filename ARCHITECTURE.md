# System Architecture: Memory-Augmented Profiling Framework

> Integrating the LongMemEval 3-stage memory framework (Indexing → Retrieval → Reading) with our profiling algorithm to build a personalized AI system evaluated on long-term memory benchmarks.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION LAYER                                 │
│                                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │calendar  │ │conversa- │ │ emails   │ │ lifelog  │ │social    │         │
│  │.jsonl    │ │tions.jsonl│ │.jsonl    │ │.jsonl    │ │posts.jsonl│        │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘         │
│       │             │            │             │             │               │
│  ┌────┴─────┐ ┌─────┴────┐ ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐        │
│  │transac-  │ │files_    │ │persona_  │ │consent   │ │summaries/│         │
│  │tions.jsonl│ │index.jsonl│ │profile  │ │.json     │ │*.json    │         │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘         │
│       └─────────────┴────────────┴─────────────┴─────────────┘              │
│                              │                                              │
│                    ┌─────────▼──────────┐                                   │
│                    │  UNIFIED SCHEMA    │                                   │
│                    │  NORMALIZER        │                                   │
│                    │                    │                                   │
│                    │  {id, ts, source,  │                                   │
│                    │   type, text, tags,│                                   │
│                    │   refs, pii_level} │                                   │
│                    └─────────┬──────────┘                                   │
└──────────────────────────────┼──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 STAGE 1: INDEXING (LongMemEval Framework)                    │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    SESSION DECOMPOSITION                             │   │
│  │                                                                      │   │
│  │  Raw events → decomposed into ROUNDS (user-turn + context)          │   │
│  │  Per LongMemEval: round-level granularity > session-level           │   │
│  │                                                                      │   │
│  │  calendar_event → {key: event_text, value: full_event, ts: ...}     │   │
│  │  ai_chat_turn  → {key: user_msg,    value: full_turn,  ts: ...}    │   │
│  │  email         → {key: subject+body, value: full_email, ts: ...}   │   │
│  │  lifelog       → {key: activity,     value: full_entry, ts: ...}   │   │
│  │  social_post   → {key: post_text,    value: full_post,  ts: ...}   │   │
│  │  transaction   → {key: description,  value: full_txn,   ts: ...}   │   │
│  └───────────────────────────┬──────────────────────────────────────────┘   │
│                              │                                              │
│  ┌───────────────────────────▼──────────────────────────────────────────┐   │
│  │                FACT-AUGMENTED KEY EXPANSION                          │   │
│  │                                                                      │   │
│  │  LLM extracts user facts from each round:                           │   │
│  │                                                                      │   │
│  │  Input:  "USER: I undercharged a client again. $600 for a brand     │   │
│  │           identity that took 40 hours..."                            │   │
│  │                                                                      │   │
│  │  Extracted facts:                                                    │   │
│  │    → "Theo charges $600 for brand identity"                         │   │
│  │    → "Theo spends 40 hours on brand identity projects"              │   │
│  │    → "Theo has pricing anxiety"                                     │   │
│  │                                                                      │   │
│  │  Key = original_text ⊕ extracted_facts (concatenated)               │   │
│  │  +9.4% recall improvement (per LongMemEval paper)                   │   │
│  └───────────────────────────┬──────────────────────────────────────────┘   │
│                              │                                              │
│  ┌───────────────────────────▼──────────────────────────────────────────┐   │
│  │              TIME-AWARE FACT ASSOCIATION                             │   │
│  │                                                                      │   │
│  │  Each fact is stamped with its source timestamp:                     │   │
│  │    {fact: "Theo charges $600", ts: "2024-01-18T23:00:00-05:00"}    │   │
│  │    {fact: "Theo raised rate",  ts: "2024-04-13T14:00:00-05:00"}    │   │
│  │                                                                      │   │
│  │  Enables temporal reasoning:                                         │   │
│  │    "What was Theo's pricing strategy in Q1 vs Q2?"                  │   │
│  └───────────────────────────┬──────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    DUAL STORAGE LAYER                                │   │
│  │                                                                      │   │
│  │  ┌─────────────────────┐    ┌─────────────────────────────────┐     │   │
│  │  │   VECTOR DB          │    │   KNOWLEDGE GRAPH (KG)          │     │   │
│  │  │   (Qdrant/Chroma)   │    │   (Neo4j / NetworkX)            │     │   │
│  │  │                     │    │                                  │     │   │
│  │  │  Stores:            │    │  Nodes:                          │     │   │
│  │  │  • Embedding(key)   │    │  • Person (Theo)                 │     │   │
│  │  │  • value (full text)│    │  • Skill (Figma, Blender...)     │     │   │
│  │  │  • metadata {ts,    │    │  • Goal (full-time freelance)    │     │   │
│  │  │    source, tags}    │    │  • Location (Austin, TX)         │     │   │
│  │  │                     │    │  • Activity (barista, design)    │     │   │
│  │  │  Index type:        │    │  • Financial (debt, income)      │     │   │
│  │  │  • Dense (Stella/   │    │  • Emotion (anxiety, confidence) │     │   │
│  │  │    GTE embeddings)  │    │  • Event (calendar items)        │     │   │
│  │  │  • Sparse (BM25)    │    │                                  │     │   │
│  │  │  • Hybrid fusion    │    │  Edges:                          │     │   │
│  │  │                     │    │  • HAS_SKILL, WANTS, LIVES_IN   │     │   │
│  │  │                     │    │  • EARNS_FROM, STRUGGLES_WITH   │     │   │
│  │  │                     │    │  • MENTIONED_AT (temporal)       │     │   │
│  │  │                     │    │  • UPDATED_TO (knowledge update) │     │   │
│  │  │                     │    │  • CO_OCCURS_WITH (cross-domain) │     │   │
│  │  └─────────────────────┘    └─────────────────────────────────┘     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 STAGE 2: RETRIEVAL (LongMemEval Framework)                   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    QUERY PROCESSING                                  │   │
│  │                                                                      │   │
│  │  User query → LLM expands with:                                     │   │
│  │    1. Time-aware expansion:                                          │   │
│  │       "How has Theo's pricing changed?" →                           │   │
│  │       "pricing, rates, invoicing | time_range: all"                 │   │
│  │                                                                      │   │
│  │    2. Semantic expansion:                                            │   │
│  │       "Is Theo confident?" →                                        │   │
│  │       "confidence, self-doubt, imposter syndrome, pricing anxiety"  │   │
│  └───────────────────────────┬──────────────────────────────────────────┘   │
│                              │                                              │
│  ┌───────────────────────────▼──────────────────────────────────────────┐   │
│  │                 HYBRID RETRIEVAL                                     │   │
│  │                                                                      │   │
│  │  1. Vector search (dense) → top-K from embedding index              │   │
│  │  2. BM25 search (sparse) → top-K from keyword index                 │   │
│  │  3. KG traversal → related nodes within N hops                      │   │
│  │  4. Temporal filter → narrow by inferred time range                  │   │
│  │  5. Reciprocal Rank Fusion → merge all result sets                  │   │
│  │                                                                      │   │
│  │  Output: ranked list of (key, value, ts, source) tuples             │   │
│  └───────────────────────────┬──────────────────────────────────────────┘   │
│                              │                                              │
│  ┌───────────────────────────▼──────────────────────────────────────────┐   │
│  │                 CROSS-SOURCE EVIDENCE ASSEMBLY                      │   │
│  │                                                                      │   │
│  │  For profiling queries, retrieve across ALL source types:           │   │
│  │                                                                      │   │
│  │  Query: "Theo's financial health"                                   │   │
│  │  → transactions (spending patterns, revenue)                        │   │
│  │  → conversations (pricing anxiety discussion)                       │   │
│  │  → emails (invoices, credit card statements)                        │   │
│  │  → lifelog (reflections on money)                                   │   │
│  │  → files_index (payoff spreadsheet)                                 │   │
│  │  → social_posts (raised rate announcement)                          │   │
│  │                                                                      │   │
│  │  Assembled into structured evidence bundle with provenance          │   │
│  └───────────────────────────┬──────────────────────────────────────────┘   │
└──────────────────────────────┼──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 STAGE 3: READING (LongMemEval Framework)                    │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                   CHAIN-OF-NOTE READER                               │   │
│  │                                                                      │   │
│  │  Retrieved evidence → LLM applies Chain-of-Note:                    │   │
│  │    1. For each retrieved item, generate a relevance note            │   │
│  │    2. Synthesize notes into coherent reasoning                       │   │
│  │    3. Handle contradictions (knowledge updates)                      │   │
│  │    4. Abstain if evidence insufficient                               │   │
│  │                                                                      │   │
│  │  +10% accuracy improvement (per LongMemEval paper)                  │   │
│  └───────────────────────────┬──────────────────────────────────────────┘   │
│                              │                                              │
│  ┌───────────────────────────▼──────────────────────────────────────────┐   │
│  │                  PROFILING ALGORITHM                                 │   │
│  │                  (Porthon Scoring Engine)                            │   │
│  │                                                                      │   │
│  │  Consumes reader output + KG state to compute:                      │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────┐     │   │
│  │  │  DIMENSION SCORES (per PROFILING_MATH.md)                  │     │   │
│  │  │                                                            │     │   │
│  │  │  Financial Literacy:  f(transactions, debt, savings_rate)  │     │   │
│  │  │  Creative Output:     f(portfolio, clients, skill_growth)  │     │   │
│  │  │  Social Bond:         f(events, posts, networking)         │     │   │
│  │  │  Self Awareness:      f(lifelog_reflections, AI_coaching)  │     │   │
│  │  │  Career Momentum:     f(income_trend, client_growth)       │     │   │
│  │  │  Well-being:          f(lifelog_mood, social_activity)     │     │   │
│  │  └────────────────────────────────────────────────────────────┘     │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────┐     │   │
│  │  │  PATTERN DETECTION                                         │     │   │
│  │  │                                                            │     │   │
│  │  │  Single-domain:  "Spending up 14% over 6 months"          │     │   │
│  │  │  Cross-domain:   "After heavy work weeks, spending         │     │   │
│  │  │                   triples — burnout cascade"               │     │   │
│  │  │                                                            │     │   │
│  │  │  Uses KG edge traversal to find cross-source correlations │     │   │
│  │  │  Uses temporal windowing on vector DB for trend detection  │     │   │
│  │  └────────────────────────────────────────────────────────────┘     │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────┐     │   │
│  │  │  SCENARIO PROJECTION                                       │     │   │
│  │  │                                                            │     │   │
│  │  │  "Comfortable Drift" → extrapolate current trends          │     │   │
│  │  │  "Rebalance"         → apply evidence-based interventions  │     │   │
│  │  │  "Transformation"    → aggressive positive change path     │     │   │
│  │  │                                                            │     │   │
│  │  │  Each scenario generates weekly action items               │     │   │
│  │  └────────────────────────────────────────────────────────────┘     │   │
│  └───────────────────────────┬──────────────────────────────────────────┘   │
└──────────────────────────────┼──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        OUTPUT LAYER                                         │
│                                                                             │
│  ┌───────────────────────┐   ┌────────────────────────────────────────┐    │
│  │  QUESTLINE UI (TSX)   │   │  PROFILER COMPARISON (HTML)            │    │
│  │  remixed-f4b73bdc.tsx │   │  theo_vs_elon_profile.html             │    │
│  │                       │   │                                        │    │
│  │  • Onboarding flow    │   │  • Radar chart (all dimensions)        │    │
│  │    (consent → loading │   │  • Score comparison bars               │    │
│  │     → patterns →      │   │  • Quadrant map (introvert/extro ×    │    │
│  │     scenarios)        │   │    reactive/strategic)                  │    │
│  │  • Dashboard          │   │  • Delta analysis cards                │    │
│  │    (stats, actions,   │   │  • Persona insight cards               │    │
│  │     chat agent)       │   │                                        │    │
│  │  • Weekly actions     │   │  Populated from profiling scores       │    │
│  │  • Pattern cards      │   │  + KG relationship data                │    │
│  │  • Scenario explorer  │   │                                        │    │
│  └───────────────────────┘   └────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     EVALUATION LAYER (LongMemEval)                          │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  HOW TO ADMINISTER                                                   │   │
│  │                                                                      │   │
│  │  1. CONVERT porthon/data → LongMemEval session format:              │   │
│  │     • Each JSONL entry becomes a timestamped session                 │   │
│  │     • conversations.jsonl → user-assistant chat sessions             │   │
│  │     • Other sources → simulated sessions where user mentions         │   │
│  │       facts from emails/lifelog/etc incidentally                     │   │
│  │                                                                      │   │
│  │  2. GENERATE evaluation questions across 5 ability types:           │   │
│  │     ┌──────────────────────┬──────────────────────────────────────┐ │   │
│  │     │ Ability              │ Example from Theo's data             │ │   │
│  │     ├──────────────────────┼──────────────────────────────────────┤ │   │
│  │     │ Info Extraction      │ "How much did Theo charge for the    │ │   │
│  │     │                      │  brand identity project?"            │ │   │
│  │     │ Multi-Session        │ "Compare Theo's pricing confidence   │ │   │
│  │     │ Reasoning            │  in Jan vs April"                    │ │   │
│  │     │ Knowledge Updates    │ "What is Theo's current hourly rate?"│ │   │
│  │     │                      │  (changed over time)                 │ │   │
│  │     │ Temporal Reasoning   │ "What skill was Theo learning in     │ │   │
│  │     │                      │  May 2024?"                          │ │   │
│  │     │ Abstention           │ "What car does Theo drive?"          │ │   │
│  │     │                      │  (never mentioned → "I don't know")  │ │   │
│  │     └──────────────────────┴──────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  3. RUN our system through the sessions sequentially                │   │
│  │     (online memory processing, not offline batch)                    │   │
│  │                                                                      │   │
│  │  4. EVALUATE using LongMemEval's GPT-4o judge:                      │   │
│  │     python3 evaluate_qa.py gpt-4o hypothesis.jsonl oracle.json      │   │
│  │                                                                      │   │
│  │  5. MEASURE:                                                         │   │
│  │     • QA Accuracy (per ability type)                                │   │
│  │     • Memory Recall@K and NDCG@K                                    │   │
│  │     • Profiling accuracy (do scores match ground truth from         │   │
│  │       master_profile.json + summaries?)                             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Data Ingestion Layer

**Input:** Porthon synthetic dataset for persona "Theo Nakamura" (p05)

| Source | File | Records | Content |
|--------|------|---------|---------|
| AI Conversations | `conversations.jsonl` | ~50 | User-AI coaching chats |
| Calendar | `calendar.jsonl` | ~50 | Events, meetings, shifts |
| Emails | `emails.jsonl` | ~50 | Client emails, bills, invoices |
| Lifelog | `lifelog.jsonl` | ~150 | Activities, reflections |
| Social Posts | `social_posts.jsonl` | ~50 | Instagram, Twitter posts |
| Transactions | `transactions.jsonl` | ~120 | Spending, revenue, subs |
| Files Index | `files_index.jsonl` | ~20 | Document references |
| Persona Profile | `persona_profile.json` | 1 | Ground truth profile |
| Consent | `consent.json` | 1 | Usage permissions |

**Unified Schema:** All sources already share a common schema:
```json
{
  "id": "string",
  "ts": "ISO-8601",
  "source": "calendar|ai_chat|email|lifelog|social|bank|files",
  "type": "event|chat_turn|sent|inbox|activity|reflection|post|transaction|doc",
  "text": "string",
  "tags": ["string"],
  "refs": ["string"],
  "pii_level": "synthetic"
}
```

### 2. Indexing Stage (per LongMemEval §4)

The paper's key insight: **memory = key-value datastore** `[(k₁,v₁), (k₂,v₂), ...]`

**Value Granularity:** Round-level (not session-level). Each JSONL entry = one round.

**Key Expansion:** LLM extracts user facts from each entry and appends to the search key:
- Original text: `"$9.99 - Figma - subscriptions"`
- Expanded key: `"$9.99 - Figma - subscriptions | Theo uses Figma | Theo pays for design software | monthly subscription expense"`

**Storage Architecture:**

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Vector DB | Qdrant / ChromaDB | Dense + sparse hybrid retrieval |
| Knowledge Graph | Neo4j / NetworkX | Entity relationships, cross-source links |
| Temporal Index | Sorted by timestamp | Time-range filtering |

**KG Schema:**
```
(:Person {name, age, location})
(:Skill {name, level, learning_since})
(:Goal {description, progress})
(:Financial {type, amount, date})
(:Activity {type, frequency})
(:Emotion {state, trigger, date})

-[:HAS_SKILL]->
-[:PURSUING]->
-[:EARNS_FROM]->
-[:STRUGGLES_WITH]->
-[:LIVES_IN]->
-[:MENTIONED_AT {ts}]->
-[:UPDATED_TO {old_value, new_value, ts}]->  // knowledge updates
-[:CO_OCCURS_WITH {correlation}]->           // cross-domain patterns
```

### 3. Retrieval Stage (per LongMemEval §5.3-5.4)

**Hybrid retrieval pipeline:**
1. **Dense search** (sentence-transformer embeddings) → semantic similarity
2. **Sparse search** (BM25) → keyword matching
3. **KG traversal** → structural relationships (e.g., "all financial facts" via edges)
4. **Temporal filter** → LLM infers time range from query, prunes results
5. **Reciprocal Rank Fusion** → merge rankings into final top-K

### 4. Reading Stage (per LongMemEval §5.5)

**Chain-of-Note reading strategy:**
1. For each retrieved memory item, LLM generates a relevance note
2. Notes are synthesized with structured JSON format
3. Contradictions resolved by preferring most recent (knowledge updates)
4. Abstention when evidence is insufficient

### 5. Profiling Algorithm

Consumes the reader's output + KG state to compute dimension scores, detect patterns, and project scenarios. This is the **Porthon scoring engine** defined in `PROFILING_MATH.md`.

**Output formats:**
- **Questline UI** (`remixed-f4b73bdc.tsx`): Interactive onboarding → dashboard with weekly actions
- **Profiler Comparison** (`theo_vs_elon_profile.html`): Radar charts, score bars, persona insights

### 6. Evaluation via LongMemEval

**Adaptation strategy:**
1. Convert porthon multi-source data into LongMemEval's session format
2. Conversations.jsonl maps directly to user-assistant sessions
3. Other sources are wrapped as sessions where the user incidentally mentions facts
4. Generate 500 questions across the 5 ability types using Theo's actual data
5. Compile histories with configurable length (S: ~115k tokens, M: ~500 sessions)
6. Run system online (sequential session processing)
7. Evaluate with `evaluate_qa.py` using GPT-4o as judge
8. Report QA accuracy + Recall@K + NDCG@K per ability type

---

## Data Flow Summary

```
porthon/data/*.jsonl
       │
       ▼
  [Normalize] ── already unified schema
       │
       ▼
  [Index] ── session decompose → fact-augment keys → timestamp-associate
       │                │
       ▼                ▼
  [Vector DB]    [Knowledge Graph]
       │                │
       ▼                ▼
  [Retrieve] ── hybrid search + KG traversal + temporal filter
       │
       ▼
  [Read] ── Chain-of-Note synthesis
       │
       ├──▶ [Profile] ── dimension scores + patterns + scenarios
       │         │
       │         ├──▶ Questline UI (TSX)
       │         └──▶ Profiler Comparison (HTML)
       │
       └──▶ [Evaluate] ── LongMemEval benchmark
                  │
                  └──▶ QA Accuracy, Recall@K, NDCG@K
```

---

## Why This Architecture

| Design Choice | Rationale (from LongMemEval paper) |
|---------------|-----------------------------------|
| Round-level granularity | Session-level loses detail; fact-level loses context. Round is optimal. |
| Fact-augmented keys | +9.4% recall improvement. Critical for indirect mentions. |
| Time-aware indexing | Temporal reasoning is weakest ability. Explicit timestamps fix this. |
| Hybrid retrieval | Dense alone misses keywords; sparse alone misses semantics. |
| KG + Vector DB dual store | KG captures structured relationships (goals, skills, finances). Vector DB captures unstructured semantic similarity. Together they cover profiling needs. |
| Chain-of-Note reading | +10% accuracy. Essential for multi-source evidence synthesis. |
| LongMemEval evaluation | ICLR 2025 benchmark. Tests all 5 memory abilities our system needs. |
