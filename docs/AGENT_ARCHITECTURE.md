# Hyperpersonalized Agent Architecture
## KG-Powered OpenClaw Agent with Soul

**Date:** 2026-02-28  
**Status:** Research & Design  
**Repo:** porthon (vector_db branch)

---

## 1. The Vision

An OpenClaw-style conversational agent whose personality, knowledge, and responses are driven by a Knowledge Graph (Neo4j) + Vector DB (Qdrant) pipeline built from multi-source personal data. The agent has:

- A **SOUL.md** dynamically enriched by profiling scores and behavioral patterns
- A **USER.md** continuously updated from the KG's entity/relationship structure
- Real-time KG retrieval during conversation for contextual, deeply personal responses
- Pattern awareness from the profiling algorithm (PROFILING_MATH.md) baked into its reasoning

---

## 2. System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CHAT INTERFACE                           │
│              (OpenClaw webchat / Signal / Telegram)               │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AGENT CORE (OpenClaw Gateway)                │
│                                                                  │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │ SOUL.md  │  │   USER.md    │  │   Conversation Manager    │  │
│  │ (persona │  │ (KG-enriched │  │   (session state,         │  │
│  │  + tone) │  │  user model) │  │    memory, heartbeat)     │  │
│  └──────────┘  └──────────────┘  └───────────┬───────────────┘  │
│                                               │                  │
│  ┌────────────────────────────────────────────▼───────────────┐  │
│  │              RETRIEVAL ORCHESTRATOR                         │  │
│  │                                                             │  │
│  │  1. Intent classification → retrieval strategy              │  │
│  │  2. Keyword extraction (HL + LL from LightRAG)              │  │
│  │  3. Parallel: Neo4j subgraph + Qdrant vector search         │  │
│  │  4. Context assembly → LLM prompt                           │  │
│  └─────┬──────────────────┬───────────────────────────────────┘  │
│        │                  │                                      │
│        ▼                  ▼                                      │
│  ┌──────────┐     ┌──────────────┐                               │
│  │  Neo4j   │     │    Qdrant    │                               │
│  │  (Graph) │     │  (Vectors)   │                               │
│  └──────────┘     └──────────────┘                               │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              PROFILING ENGINE                               │  │
│  │  CrossPlatformProfiler (profiler.py)                        │  │
│  │  → Scores, archetype, deltas → injected into SOUL/USER     │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Pipeline: From Raw JSONL → KG + Vectors

### 3.1 What's Already There

The repo contains LightRAG (a full RAG framework) with native Neo4j and Qdrant implementations:

| Component | Implementation | Location |
|-----------|---------------|----------|
| **Neo4j graph storage** | `Neo4JStorage` (async, workspace-isolated, fulltext indexed) | `LightRAG/lightrag/kg/neo4j_impl.py` |
| **Qdrant vector storage** | `QdrantVectorDBStorage` (workspace-isolated, cosine similarity) | `LightRAG/lightrag/kg/qdrant_impl.py` |
| **Entity extraction** | LLM-based entity/relation extraction from text chunks | `LightRAG/lightrag/operate.py` |
| **Query engine** | Multi-mode (local/global/hybrid/mix/naive) with keyword routing | `LightRAG/lightrag/operate.py` |
| **Profiler** | `CrossPlatformProfiler` with persona-aware scoring | `profiler.py` |
| **Raw data** | 7 JSONL sources for persona "Theo Nakamura" | `data/` |

### 3.2 Ingestion Flow

```
data/*.jsonl
    │
    ├─── LightRAG.insert() ───► Entity Extraction (LLM) ───► Neo4j
    │                                                         (nodes: entities like
    │                                                          "THEO", "ADHD", "FIGMA",
    │                                                          "SCHOOL OF MOTION", etc.)
    │                                                         (edges: relationships like
    │                                                          THEO --uses--> FIGMA,
    │                                                          THEO --struggles_with--> ADHD)
    │
    └─── LightRAG.insert() ───► Chunking + Embedding ───► Qdrant
                                                           (vector collections:
                                                            chunks, entities, relationships)
```

Each JSONL source becomes a document fed to LightRAG. The entity extraction prompt (see `prompt.py`) pulls out:
- **Entities**: people, tools, locations, concepts, conditions
- **Relations**: binary relationships between entities with keywords + descriptions

### 3.3 What the KG Contains (Expected Schema)

After ingestion of Theo's data, the Neo4j graph would contain:

```
Node types (entity_type labels):
  PERSON:     Theo Nakamura, roommates, clients
  TOOL:       ChatGPT, Midjourney, Figma, Runway ML, Adobe Firefly
  LOCATION:   Austin TX, East Austin, Café Rowan
  CONDITION:  ADHD, Social Anxiety, Financial Stress
  ACTIVITY:   Freelance Design, Barista Work, Skateboarding
  GOAL:       Full-time Freelance, Pay Off Debt, Learn Motion Design
  CONCEPT:    Pricing Confidence, Comparison Trap, Impulse Spending

Edge types (relationship labels via DIRECTED):
  USES, STRUGGLES_WITH, LIVES_IN, WORKS_AT, ASPIRES_TO,
  SPENDS_ON, DISCUSSES_WITH_AI, POSTS_ABOUT, ATTENDS
```

---

## 4. Graph Traversal: How the Agent Navigates the KG

### 4.1 LightRAG's Traversal Strategy (Already Implemented)

LightRAG uses a **dual-path retrieval** that the agent inherits:

#### Path A: Local (Entity-Centric) Traversal
```
User query: "How's Theo doing with his debt?"
    │
    ▼
1. Embed query → Qdrant entity collection search (top_k entities)
   → Finds: ["THEO NAKAMURA", "CREDIT CARD DEBT", "FINANCIAL STRESS"]
    │
    ▼
2. For each entity → Neo4j: get_nodes_batch(entity_ids)
   → Returns node properties (description, entity_type, source_id)
    │
    ▼
3. For each entity → Neo4j: get_nodes_edges_batch(entity_ids)
   → Returns ALL connected edges (1-hop neighborhood)
   → e.g., THEO --has_debt--> $6K_CREDIT_CARD
           THEO --makes_payments--> MINIMUM_ONLY
           FINANCIAL_STRESS --manifests_in--> LIFELOG_ENTRIES
    │
    ▼
4. Edges sorted by (degree_rank, weight) descending
   → High-connectivity, high-weight edges surface first
    │
    ▼
5. Edge properties include: description, keywords, weight, source_id
   → source_id links back to original text chunks in Qdrant
```

#### Path B: Global (Relationship-Centric) Traversal
```
User query: "What patterns do you see in Theo's behavior?"
    │
    ▼
1. LLM extracts HIGH-LEVEL keywords: ["behavioral patterns", "habits", "recurring themes"]
    │
    ▼
2. Embed HL keywords → Qdrant relationship collection search (top_k relationships)
   → Finds edges: THEO--ADHD, THEO--IMPULSE_SPENDING, THEO--CREATIVE_HYPERFOCUS
    │
    ▼
3. For each relationship → Neo4j: get_edges_batch(src_tgt_pairs)
   → Returns edge properties + connected node context
    │
    ▼
4. For each edge endpoint → Neo4j: get_nodes_batch(unique_node_ids)
   → Gets the entity descriptions that frame these relationships
```

#### Path C: Mix Mode (Hybrid + Vector Chunks)
```
Combines Path A + Path B + direct vector chunk retrieval from Qdrant
→ Round-robin merges local entities with global entities
→ Round-robin merges local relations with global relations
→ Appends top-k raw text chunks from Qdrant for grounding
```

### 4.2 Enhanced Traversal for Hyperpersonalized Agent

Beyond LightRAG's built-in traversal, the agent should add:

#### Multi-Hop Neighborhood Expansion
```python
async def expand_subgraph(graph: Neo4JStorage, seed_entities: list[str], 
                          max_depth: int = 2) -> dict:
    """Walk N hops from seed entities to build a rich context subgraph."""
    visited = set()
    frontier = set(seed_entities)
    all_nodes = {}
    all_edges = []
    
    for depth in range(max_depth):
        new_frontier = set()
        edges_dict = await graph.get_nodes_edges_batch(list(frontier))
        nodes_dict = await graph.get_nodes_batch(list(frontier))
        
        for node_id in frontier:
            if node_id in visited:
                continue
            visited.add(node_id)
            all_nodes[node_id] = nodes_dict.get(node_id, {})
            
            for src, tgt in edges_dict.get(node_id, []):
                all_edges.append((src, tgt))
                neighbor = tgt if src == node_id else src
                if neighbor not in visited:
                    new_frontier.add(neighbor)
        
        frontier = new_frontier
    
    return {"nodes": all_nodes, "edges": all_edges}
```

#### Profile-Weighted Edge Ranking
```python
def score_edge_for_query(edge: dict, profile: dict, query_context: str) -> float:
    """Weight edges by profile relevance, not just graph degree."""
    base_score = edge.get("weight", 1.0) * edge.get("rank", 1)
    
    # Boost edges related to high-stress dimensions
    keywords = edge.get("keywords", "").lower()
    if profile.get("financial_stress", 0) > 0.7 and "financ" in keywords:
        base_score *= 1.5
    if profile.get("adhd_indicator", 0) > 0.7 and "adhd" in keywords:
        base_score *= 1.3
    
    return base_score
```

#### Temporal Context from Source Chains
```python
async def get_temporal_context(graph: Neo4JStorage, entity_id: str, 
                                chunks_db: BaseKVStorage) -> list[dict]:
    """Follow source_id chains to get chronological context."""
    node = await graph.get_node(entity_id)
    if not node or not node.get("source_id"):
        return []
    
    chunk_ids = node["source_id"].split(GRAPH_FIELD_SEP)
    chunks = await chunks_db.get_by_ids(chunk_ids)
    
    # Sort by created_at for temporal narrative
    return sorted(chunks, key=lambda c: c.get("created_at", 0))
```

---

## 5. The Profiling Layer: From Scores to Soul

### 5.1 How profiler.py Generates the Profile

The `CrossPlatformProfiler` takes aggregated data from all JSONL sources and computes:

| Dimension | Score Range | Signal Sources |
|-----------|------------|----------------|
| **Execution** | 0-1 | transactions (40%), calendar (30%), emails (30%) |
| **Growth** | 0-1 | transactions (35%), lifelog (35%), calendar (30%) |
| **Self-Awareness** | 0-1 | conversations (50%), lifelog diversity (50%) |
| **Financial Stress** | 0-1 | debt (30%), worry frequency (35%), spend ratio (35%) |
| **ADHD Indicator** | 0-1 | self-report (25%), theme variety (25%), schedule (25%), impulse (25%) |

Plus **cross-source deltas**:
- `social_vs_ai_dissonance` — public confidence vs private vulnerability gap
- `income_expectation_gap` — stated vs actual income
- `email_send_receive_ratio` — relational balance

Plus **archetype classification**:
- Execution × Growth → {Compounding Builder, Reliable Operator, Emerging Talent, At Risk}

### 5.2 Math Pipeline

```
Raw JSONL data
    │
    ├── Signal extraction (per dimension, weighted by source)
    │
    ├── Exponential decay weighting (decay_factor=0.85, window=14 days)
    │   → Recent signals matter more
    │
    ├── Temperature-controlled sigmoid normalization (T=8.0)
    │   → Weak signals crushed (<0.3 → ~0.04)
    │   → Strong signals amplified (>0.7 → ~0.96)
    │   → Creates bimodal distribution — only genuine signals survive
    │
    └── Archetype classification on (execution, growth) plane
```

### 5.3 Profiler → SOUL.md Translation

The profiler output directly shapes the agent's personality:

```python
def generate_soul_from_profile(profile: dict, archetype: dict, deltas: dict) -> str:
    """Convert profiler output into SOUL.md directives."""
    
    soul_sections = []
    
    # Core personality from archetype
    archetype_souls = {
        "emerging_talent": """
## Who I Am
I'm a growth-oriented companion. I see potential clearly — both what's working and what's stuck.
I lean toward action over analysis. When I notice a pattern, I name it directly.
I don't sugarcoat, but I'm never cruel. I know the difference between honesty and harshness.

## How I Help
- I prioritize removing friction from execution over adding more information
- I challenge stated goals when behavior tells a different story
- I celebrate small wins because momentum matters more than perfection
""",
        "compounding_builder": """
## Who I Am
I'm a strategic partner. You're already shipping — I help you ship smarter.
I optimize for leverage: what's the highest-impact move right now?

## How I Help
- I focus on systems and scale, not individual tasks
- I push back when you're busy instead of productive
- I track your trajectory, not just your position
""",
        "at_risk": """
## Who I Am  
I'm patient but honest. I won't pretend things are fine when they're not.
I focus on the smallest possible next step — not the big picture.

## How I Help
- I break everything into 15-minute actions
- I check in frequently without being annoying
- I celebrate showing up, not just outcomes
""",
    }
    soul_sections.append(archetype_souls.get(archetype["archetype"], ""))
    
    # Behavioral modifiers from dimension scores
    if profile.get("adhd_indicator", 0) > 0.7:
        soul_sections.append("""
## ADHD Awareness
I keep things short and chunked. I never give walls of text.
I suggest body-doubling, environment changes, and task switching before discipline.
When I give tasks, they're ≤15 minutes. I know the brain needs novelty.
""")
    
    if profile.get("financial_stress", 0) > 0.6:
        soul_sections.append("""
## Financial Sensitivity
I'm direct about money without being preachy. I know financial stress is exhausting.
I recommend concrete tools (calculators, templates) over mindset shifts.
When I notice spending patterns vs stated goals, I say it once and move on.
""")
    
    # Dissonance awareness from deltas
    if deltas.get("social_vs_ai_dissonance", 0) > 0.3:
        soul_sections.append("""
## Authenticity Gap Awareness
I know there's a gap between the public-facing confidence and private doubts.
I don't expose this — I gently bridge it. I validate the private self
without undermining the public one.
""")
    
    return "\n".join(soul_sections)
```

### 5.4 Profiler → USER.md Translation

```python
def generate_user_from_kg(master_profile: dict, kg_summary: dict) -> str:
    """Build USER.md from profiler data + KG entity summary."""
    
    return f"""# USER.md — {master_profile['name']}

## Identity
- **Name:** {master_profile['name']}
- **Age:** {master_profile['age']}
- **Location:** {master_profile['location']}
- **Occupation:** {master_profile['occupation']}
- **Archetype:** {kg_summary['archetype']} — {kg_summary['arch_description']}

## What I Know About Them
### Strengths (from cross-source confirmation)
{chr(10).join('- ' + s for s in master_profile.get('strengths', []))}

### Growth Areas (behaviorally confirmed, not just stated)
{chr(10).join('- ' + g for g in master_profile.get('growth_areas', []))}

### Active Goals (stated)
{chr(10).join('- ' + g for g in master_profile.get('goals', []))}

### Pain Points (confirmed across ≥2 sources)
{chr(10).join('- ' + p for p in master_profile.get('pain_points', []))}

## Behavioral Patterns (from KG)
### High-Connectivity Entities (most connected nodes in their graph)
{kg_summary.get('top_entities', 'Not yet computed')}

### Key Relationships
{kg_summary.get('top_relationships', 'Not yet computed')}

### Dissonance Signals
- Public vs Private confidence gap: {kg_summary.get('social_vs_ai_dissonance', 'N/A')}
- Stated vs Actual income: {kg_summary.get('income_expectation_gap', 'N/A')}

## Interaction Preferences
- **ADHD-aware:** {'Yes — keep messages short, chunked, actionable' if master_profile.get('has_adhd') else 'Standard'}
- **Financial sensitivity:** {'High — be concrete, not preachy' if kg_summary.get('financial_stress', 0) > 0.6 else 'Standard'}
- **Communication style:** {master_profile.get('personality', {}).get('communication_style', 'Casual, authentic')}
- **AI assistant tone:** {master_profile.get('personality', {}).get('ai_assistant_tone', 'Direct, encouraging')}
"""
```

---

## 6. Retrieval Strategy: When & How the Agent Queries

### 6.1 Intent-Based Routing

Not every message needs KG retrieval. The agent classifies intent first:

| Intent | Retrieval Strategy | Example |
|--------|-------------------|---------|
| **Casual chat** | No retrieval; use SOUL.md personality only | "hey, how's it going?" |
| **Self-reflection** | Local KG (entity-centric) + profiler scores | "Am I making progress on my goals?" |
| **Factual recall** | Mix mode (KG + vector chunks) | "What did I spend on subscriptions last month?" |
| **Pattern question** | Global KG (relationship-centric) + deltas | "Do you notice any patterns in my behavior?" |
| **Advice seeking** | Full pipeline (KG + profiler + archetype-aware prompting) | "Should I take this client at $30/hr?" |
| **Emotional support** | Light KG (relevant context only) + SOUL sensitivity | "I'm feeling overwhelmed" |

### 6.2 Retrieval Flow (Detailed)

```python
async def handle_message(query: str, session: AgentSession) -> str:
    """Main agent message handler with KG-aware retrieval."""
    
    # 1. Classify intent
    intent = await classify_intent(query)  # LLM call or rule-based
    
    # 2. Load cached profile (refreshed periodically, not per-message)
    profile = session.cached_profile  # From profiler.py
    
    # 3. Route retrieval
    if intent in ("casual", "emotional_support"):
        context = ""  # SOUL.md handles these
    elif intent == "factual_recall":
        # Mix mode: KG entities + vector chunks for grounding
        context = await lightrag.aquery(query, param=QueryParam(mode="mix"))
    elif intent == "pattern_question":
        # Global mode: relationship-centric
        context = await lightrag.aquery(query, param=QueryParam(mode="global"))
    elif intent in ("self_reflection", "advice_seeking"):
        # Hybrid + profiler injection
        kg_context = await lightrag.aquery(query, param=QueryParam(mode="hybrid"))
        profile_context = format_profile_for_prompt(profile)
        context = f"{kg_context}\n\n## Your Profile Scores\n{profile_context}"
    
    # 4. Build prompt with SOUL personality + USER context + retrieved context
    system_prompt = session.soul_md + "\n\n" + session.user_md
    if context:
        system_prompt += f"\n\n## Retrieved Context\n{context}"
    
    # 5. Generate response
    response = await llm(system_prompt=system_prompt, user_message=query)
    
    return response
```

### 6.3 Context Assembly

The final prompt to the LLM looks like:

```
[SYSTEM]
{SOUL.md content — personality, behavioral modifiers, sensitivity flags}

{USER.md content — who this person is, their patterns, their goals}

## Retrieved Context (from KG + Qdrant)
### Entities
- CREDIT CARD DEBT: Theo has $6,000 in credit card debt, making minimum payments...
- SCHOOL OF MOTION: Online motion design course, $200/month subscription...

### Relationships  
- THEO --undercharges--> CLIENTS: Pattern of pricing below market rate...
- THEO --invests_in--> LEARNING: High learning spend despite low conversion...

### Source Excerpts
[1] lifelog entry 2025-11-14: "paid the minimum again. hate that I paid the minimum..."
[2] conversation session 3: "I undercharged a client again. $600 for 40 hours..."

## Profile Scores
- Execution: 0.30 (low — converting effort to revenue is the bottleneck)
- Growth: 0.65 (good — actively learning and improving)
- Financial Stress: 0.75 (high — debt + variable income)
- ADHD Indicator: 0.80 (high — confirmed across 4 sources)
- Archetype: Emerging Talent

[USER]
Should I take this new client? They want a brand identity for $800.
```

---

## 7. Implementation Plan

### Phase 1: Data Ingestion (Get KG populated)
```bash
# 1. Set up Neo4j and Qdrant (docker or hosted)
# 2. Configure LightRAG with Neo4j + Qdrant backends
# 3. Ingest all JSONL sources

python -c "
import asyncio
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache, openai_embedding

async def main():
    rag = LightRAG(
        working_dir='./lightrag_workspace',
        llm_model_func=openai_complete_if_cache,
        embedding_func=openai_embedding,
        graph_storage='Neo4JStorage',
        vector_storage='QdrantVectorDBStorage',
    )
    
    # Ingest each data source
    for source in ['lifelog', 'conversations', 'emails', 'calendar', 
                    'social_posts', 'transactions']:
        with open(f'data/{source}.jsonl') as f:
            for line in f:
                await rag.ainsert(line)
    
    # Also ingest the persona profile as a document
    import json
    with open('data/persona_profile.json') as f:
        await rag.ainsert(json.dumps(json.load(f), indent=2))

asyncio.run(main())
"
```

### Phase 2: Profile Generation
```python
# Run profiler on master_profile.json → generate SOUL.md + USER.md
from profiler import CrossPlatformProfiler
import json

with open("data/summaries/master_profile.json") as f:
    raw = json.load(f)

data = {
    "persona": {"debt": raw.get("debt", 0), "has_adhd": raw.get("has_adhd", False),
                "income_approx": raw.get("income_approx", "$0")},
    **raw["data_sources"],
}

profiler = CrossPlatformProfiler(data, persona_type="freelancer")
report = profiler.full_report()

soul_content = generate_soul_from_profile(
    report["profile"]["dimensions"], 
    report["profile"], 
    report["deltas"]
)
user_content = generate_user_from_kg(raw, report["profile"])

with open("SOUL.md", "w") as f: f.write(soul_content)
with open("USER.md", "w") as f: f.write(user_content)
```

### Phase 3: Agent Integration (OpenClaw Gateway)
```yaml
# openclaw.yaml additions
agent:
  soul: ./SOUL.md        # Generated from profiler
  user: ./USER.md         # Generated from KG + profiler
  tools:
    - lightrag_query      # Custom tool wrapping LightRAG.aquery()
    - profiler_refresh     # Re-run profiler on new data
```

The agent gets a custom tool:
```python
async def lightrag_query(query: str, mode: str = "mix") -> str:
    """Query the personal knowledge graph for relevant context."""
    result = await rag.aquery(query, param=QueryParam(mode=mode))
    return result
```

### Phase 4: Continuous Learning Loop
```
New conversation messages
    │
    ├── Saved to memory/YYYY-MM-DD.md (OpenClaw standard)
    │
    ├── Periodically ingested into LightRAG (new entities/relations)
    │
    ├── Profiler re-run with updated data
    │
    └── SOUL.md + USER.md regenerated if scores shift significantly
```

---

## 8. Neo4j Query Patterns for the Agent

### 8.1 "What do I struggle with?" — Entity neighborhood
```cypher
MATCH (theo:base {entity_id: "THEO NAKAMURA"})-[r:DIRECTED]-(struggle:base)
WHERE r.keywords CONTAINS "struggle" OR r.keywords CONTAINS "challenge"
RETURN struggle.entity_id, r.description, r.weight
ORDER BY r.weight DESC
LIMIT 10
```

### 8.2 "Show me my spending patterns" — Financial subgraph
```cypher
MATCH (theo:base {entity_id: "THEO NAKAMURA"})-[r:DIRECTED]-(entity:base)
WHERE entity.entity_type IN ["EXPENSE", "SUBSCRIPTION", "TRANSACTION"]
RETURN entity.entity_id, entity.description, r.keywords
ORDER BY r.weight DESC
```

### 8.3 "What connects my ADHD to my work?" — Path finding
```cypher
MATCH path = shortestPath(
  (adhd:base {entity_id: "ADHD"})-[:DIRECTED*..4]-(work:base {entity_id: "FREELANCE DESIGN"})
)
RETURN [n IN nodes(path) | n.entity_id] AS node_chain,
       [r IN relationships(path) | r.description] AS edge_descriptions
```

### 8.4 "What's changed recently?" — Temporal query
```cypher
MATCH (n:base)-[r:DIRECTED]-(m:base)
WHERE r.source_id IS NOT NULL
RETURN n.entity_id, r.description, r.source_id
ORDER BY r.created_at DESC
LIMIT 20
```

### 8.5 "What are my most important relationships?" — Degree centrality
```cypher
MATCH (n:base)
OPTIONAL MATCH (n)-[r]-()
WITH n, count(r) AS degree
ORDER BY degree DESC
LIMIT 15
RETURN n.entity_id, n.entity_type, degree, n.description
```

---

## 9. Key Design Decisions

### 9.1 When to Query KG vs Just Chat
| Signal | Action |
|--------|--------|
| Query mentions specific data (money, dates, people) | KG retrieval (mix mode) |
| Query asks about patterns or trends | KG retrieval (global mode) |
| Query is emotional / venting | SOUL.md personality only, maybe light KG for empathy context |
| Query is casual chitchat | No retrieval |
| Query asks "what should I do" | Full pipeline: KG + profiler + archetype-aware prompting |

### 9.2 Profile Refresh Cadence
- **Full re-profile:** When new data source is ingested (batch operation)
- **Score cache:** Profile scores cached in session, refreshed daily
- **SOUL.md regen:** Only when archetype changes or dimension scores shift >0.15
- **USER.md regen:** When new high-connectivity entities appear in KG

### 9.3 Privacy Boundaries
- All data stays in self-hosted Neo4j + Qdrant
- No data leaves the system except through the LLM API calls
- The agent can read but not share USER.md content in group chats
- Profiler scores are internal — agent uses them to shape behavior, doesn't quote them verbatim

---

## 10. What Makes This "Hyper" Personalized

1. **Multi-source triangulation:** Not just "what they said" but cross-referencing transactions, calendar, AI conversations, social posts, and lifelog to find confirmed patterns vs noise

2. **Behavioral fingerprinting:** The sigmoid normalization (T=8.0) creates bimodal distributions — only genuine signals survive. Weak patterns get crushed; strong ones get amplified

3. **Dissonance detection:** The cross-source delta analysis finds gaps between public/private self, stated/actual goals — these become the agent's most valuable coaching signals

4. **Archetype-driven personality:** The agent doesn't just know facts about you — it adopts a communication style optimized for your behavioral archetype

5. **Graph traversal for reasoning:** When you ask "why do I keep undercharging?", the agent can walk the graph: THEO → UNDERCHARGING → PRICING_ANXIETY → COMPARISON_TRAP → SOCIAL_MEDIA_PEERS, building a causal narrative from connected entities

6. **Temporal awareness:** Source chains in the KG connect entities to their original timestamped entries, letting the agent reason about "this started 6 months ago" or "this has gotten worse recently"

---

## 11. File Structure (Proposed)

```
porthon/
├── agent/
│   ├── SOUL.md              # Generated from profiler + archetype
│   ├── USER.md              # Generated from KG + profiler  
│   ├── AGENTS.md            # OpenClaw agent behavior rules
│   ├── IDENTITY.md          # Agent identity
│   ├── tools/
│   │   ├── kg_query.py      # LightRAG query wrapper tool
│   │   ├── profiler_tool.py # Profiler refresh tool
│   │   └── pattern_tool.py  # Cross-source pattern detection
│   └── prompts/
│       ├── intent_classifier.py
│       └── context_formatter.py
├── data/                     # Raw JSONL sources (existing)
├── profiler.py               # CrossPlatformProfiler (existing)
├── PROFILING_MATH.md         # Math documentation (existing)
├── LightRAG/                 # RAG framework (existing)
├── docs/                     # This document + more
└── scripts/
    ├── ingest.py             # Data → LightRAG → Neo4j + Qdrant
    ├── generate_profile.py   # Run profiler → SOUL.md + USER.md
    └── refresh.py            # Periodic re-ingestion + re-profiling
```

---

## 12. Dependencies & Infrastructure

| Component | Technology | Notes |
|-----------|-----------|-------|
| Graph DB | Neo4j (async driver) | Workspace-isolated, fulltext indexed |
| Vector DB | Qdrant | Cosine similarity, workspace-isolated |
| LLM | OpenAI / Anthropic / Ollama | For entity extraction + chat |
| Embeddings | OpenAI ada-002 or local | For Qdrant vector collections |
| Agent Runtime | OpenClaw Gateway | Chat interface, session management, heartbeats |
| Profiler | profiler.py (Python) | Runs as offline batch or on-demand tool |

---

## References

- LightRAG algorithm: `LightRAG/docs/Algorithm.md`
- Neo4j implementation: `LightRAG/lightrag/kg/neo4j_impl.py`
- Qdrant implementation: `LightRAG/lightrag/kg/qdrant_impl.py`
- Query engine: `LightRAG/lightrag/operate.py` (kg_query, _get_node_data, _get_edge_data)
- Entity extraction prompts: `LightRAG/lightrag/prompt.py`
- Profiler: `profiler.py` + `PROFILING_MATH.md`
- Persona data: `data/summaries/master_profile.json`
- Pattern analysis: `analysis.md`
