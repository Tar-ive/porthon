# System Architecture: Memory-Augmented Profiling Framework

> Integrating **NLWeb** (Microsoft's conversational protocol layer) + **LongMemEval** 3-stage memory framework + our **profiling algorithm** to build a personalized AI system with natural language interfaces, MCP compatibility, and long-term memory evaluation.

---

## What Changed: Why NLWeb

NLWeb is **not** a memory system — it's a **conversational protocol layer** that sits in front of any data backend. Think of it as "HTML for the AI web." It provides:

1. **A REST/MCP protocol** (`/ask`, `/mcp`) that returns Schema.org JSON
2. **A query processing pipeline**: decontextualize → retrieve → rank → respond
3. **Mixed-mode programming**: dozens of small, precise LLM calls controlled by code
4. **Tool system**: Search, Item Details, Ensemble Queries — extensible
5. **Built-in memory hooks**: detect what to remember, pass context across turns
6. **Fast-track path**: parallel optimistic execution for common queries

**For our project, NLWeb becomes the interface layer** — the conversational API that humans and AI agents use to query Theo's profile. Our LongMemEval memory system becomes NLWeb's backend. The profiler becomes a custom NLWeb tool.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLIENTS / CONSUMERS                                 │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Questline UI │  │ Profiler HTML│  │ MCP Agents   │  │ External     │   │
│  │ (React TSX)  │  │ (Comparison) │  │ (Claude,     │  │ NLWeb Sites  │   │
│  │              │  │              │  │  Copilot...) │  │ (federated)  │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         └──────────────────┴─────────────────┴─────────────────┘           │
│                                    │                                        │
│                          REST /ask + /mcp                                   │
│                         Schema.org JSON responses                           │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌═════════════════════════════════════════════════════════════════════════════┐
║                     NLWeb CONVERSATIONAL LAYER                              ║
║                     (Protocol + Query Processing Engine)                     ║
║                                                                             ║
║  ┌─────────────────────────────────────────────────────────────────────┐   ║
║  │                    REQUEST INITIALIZATION                           │   ║
║  │                                                                     │   ║
║  │  POST /ask {query, site, prev, mode, streaming}                    │   ║
║  │  POST /mcp {call_tool: "ask", query, ...}                         │   ║
║  │                                                                     │   ║
║  │  NLWebHandler → NLWebHandlerState → session context                │   ║
║  └──────────────────────────┬──────────────────────────────────────────┘   ║
║                             │                                              ║
║  ┌──────────────────────────▼──────────────────────────────────────────┐   ║
║  │              PARALLEL PRE-RETRIEVAL ANALYSIS                        │   ║
║  │              (~5-10 LLM micro-calls in parallel)                    │   ║
║  │                                                                     │   ║
║  │  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐          │   ║
║  │  │ Relevance      │ │ Decontextualize│ │ Memory         │          │   ║
║  │  │ Detection      │ │                │ │ Detection      │          │   ║
║  │  │                │ │ "How's his     │ │                │          │   ║
║  │  │ Is this about  │ │  debt?" →      │ │ "Remember:     │          │   ║
║  │  │ Theo's profile?│ │ "How is Theo   │ │  Theo prefers  │          │   ║
║  │  │                │ │  Nakamura's    │ │  informal      │          │   ║
║  │  │                │ │  credit card   │ │  tone"         │          │   ║
║  │  │                │ │  debt?"        │ │                │          │   ║
║  │  └────────────────┘ └────────────────┘ └───────┬────────┘          │   ║
║  │  ┌────────────────┐ ┌────────────────┐         │                   │   ║
║  │  │ Required Info   │ │ Query Rewrite  │  ┌──────▼──────────┐       │   ║
║  │  │                │ │                │  │ MEMORY STORE     │       │   ║
║  │  │ "Need time     │ │ Expand for     │  │ (persistent)     │       │   ║
║  │  │  range for     │ │ retrieval      │  │                  │       │   ║
║  │  │  trend query"  │ │                │  │ User preferences │       │   ║
║  │  └────────────────┘ └────────────────┘  │ + session facts  │       │   ║
║  │                                          └─────────────────┘       │   ║
║  │  ── FAST TRACK ──────────────────────────────────────────────      │   ║
║  │  Launched in parallel: optimistic retrieval for simple queries      │   ║
║  └──────────────────────────┬──────────────────────────────────────────┘   ║
║                             │                                              ║
║  ┌──────────────────────────▼──────────────────────────────────────────┐   ║
║  │              TOOL SELECTION & ROUTING                                │   ║
║  │              (LLM selects from tools.xml)                           │   ║
║  │                                                                     │   ║
║  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   ║
║  │  │ Profile      │  │ Memory       │  │ Pattern      │              │   ║
║  │  │ Search Tool  │  │ Query Tool   │  │ Analysis Tool│              │   ║
║  │  │              │  │              │  │              │              │   ║
║  │  │ "What are    │  │ "What did    │  │ "What's      │              │   ║
║  │  │  Theo's      │  │  Theo say    │  │  driving     │              │   ║
║  │  │  skills?"    │  │  about rates │  │  his spending│              │   ║
║  │  │              │  │  in January?"│  │  spikes?"    │              │   ║
║  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │   ║
║  │  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────┴───────┐              │   ║
║  │  │ Scenario     │  │ Comparison   │  │ Action       │              │   ║
║  │  │ Projection   │  │ Tool         │  │ Recommender  │              │   ║
║  │  │ Tool         │  │              │  │ Tool         │              │   ║
║  │  │              │  │ "Compare     │  │              │              │   ║
║  │  │ "What if     │  │  Theo vs     │  │ "What should │              │   ║
║  │  │  trends      │  │  Elon on     │  │  Theo do     │              │   ║
║  │  │  continue?"  │  │  financial   │  │  this week?" │              │   ║
║  │  │              │  │  literacy"   │  │              │              │   ║
║  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │   ║
║  │         └─────────────────┴─────────────────┘                      │   ║
║  │                           │                                         │   ║
║  └───────────────────────────┼─────────────────────────────────────────┘   ║
║                              │ Tools call into Memory Backend ↓            ║
╚══════════════════════════════╪═════════════════════════════════════════════╝
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              LONGMEMEVAL MEMORY BACKEND                                     │
│              (3-Stage: Index → Retrieve → Read)                             │
│                                                                             │
│  ╔═══════════════════════════════════════════════════════════════════════╗  │
│  ║  STAGE 1: INDEXING                                                    ║  │
│  ║                                                                       ║  │
│  ║  Data Ingestion (porthon/data/)                                      ║  │
│  ║  ┌──────────┬──────────┬──────────┬──────────┬──────────┬─────────┐  ║  │
│  ║  │calendar  │conversa- │emails    │lifelog   │social    │transac- │  ║  │
│  ║  │.jsonl    │tions.jsonl│.jsonl   │.jsonl    │posts.jsonl│tions   │  ║  │
│  ║  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬────┘  ║  │
│  ║       └──────────┴──────────┴──────────┴──────────┴──────────┘       ║  │
│  ║                              │                                        ║  │
│  ║                    Unified Schema (already shared):                    ║  │
│  ║                    {id, ts, source, type, text, tags, refs}           ║  │
│  ║                              │                                        ║  │
│  ║               ┌──────────────▼──────────────┐                         ║  │
│  ║               │  ROUND-LEVEL DECOMPOSITION  │                         ║  │
│  ║               │  Each JSONL entry = 1 round  │                         ║  │
│  ║               └──────────────┬──────────────┘                         ║  │
│  ║                              │                                        ║  │
│  ║               ┌──────────────▼──────────────┐                         ║  │
│  ║               │  FACT-AUGMENTED KEY          │                         ║  │
│  ║               │  EXPANSION (LLM)             │                         ║  │
│  ║               │                              │                         ║  │
│  ║               │  text + extracted_facts →     │                         ║  │
│  ║               │  expanded search key          │                         ║  │
│  ║               │  (+9.4% recall per paper)     │                         ║  │
│  ║               └──────────────┬──────────────┘                         ║  │
│  ║                              │                                        ║  │
│  ║               ┌──────────────▼──────────────┐                         ║  │
│  ║               │  TIME-AWARE FACT             │                         ║  │
│  ║               │  ASSOCIATION                 │                         ║  │
│  ║               │                              │                         ║  │
│  ║               │  Each fact stamped with ts   │                         ║  │
│  ║               │  from source event           │                         ║  │
│  ║               └──────────────┬──────────────┘                         ║  │
│  ║                              │                                        ║  │
│  ╚══════════════════════════════╪════════════════════════════════════════╝  │
│                                 │                                          │
│  ╔══════════════════════════════╪════════════════════════════════════════╗  │
│  ║  DUAL STORAGE LAYER          ▼                                        ║  │
│  ║                                                                       ║  │
│  ║  ┌───────────────────────────────┐  ┌──────────────────────────────┐  ║  │
│  ║  │     VECTOR DB (Qdrant)        │  │   KNOWLEDGE GRAPH (Neo4j)    │  ║  │
│  ║  │                               │  │                              │  ║  │
│  ║  │  NLWeb retriever.py connects  │  │  Nodes:                      │  ║  │
│  ║  │  here via DB abstraction      │  │  (:Person), (:Skill),        │  ║  │
│  ║  │                               │  │  (:Goal), (:Financial),      │  ║  │
│  ║  │  Collections:                 │  │  (:Activity), (:Emotion),    │  ║  │
│  ║  │  • theo_memories (all rounds) │  │  (:Event), (:Location)       │  ║  │
│  ║  │  • theo_facts (extracted)     │  │                              │  ║  │
│  ║  │                               │  │  Edges:                      │  ║  │
│  ║  │  Each entry = Schema.org obj: │  │  -[:HAS_SKILL]->             │  ║  │
│  ║  │  {                            │  │  -[:PURSUING]->              │  ║  │
│  ║  │    "@type": "DataFeedItem",   │  │  -[:EARNS_FROM]->           │  ║  │
│  ║  │    "dateCreated": ts,         │  │  -[:STRUGGLES_WITH]->       │  ║  │
│  ║  │    "name": key,               │  │  -[:UPDATED_TO {ts}]->      │  ║  │
│  ║  │    "description": value,      │  │  -[:CO_OCCURS_WITH]->       │  ║  │
│  ║  │    "keywords": tags,          │  │                              │  ║  │
│  ║  │    "sourceOrganization": src  │  │  Queried by KG traversal    │  ║  │
│  ║  │  }                            │  │  tool in NLWeb pipeline      │  ║  │
│  ║  │                               │  │                              │  ║  │
│  ║  │  NLWeb expects Schema.org!    │  │                              │  ║  │
│  ║  └───────────────────────────────┘  └──────────────────────────────┘  ║  │
│  ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                 │                                          │
│  ╔══════════════════════════════╪════════════════════════════════════════╗  │
│  ║  STAGE 2: RETRIEVAL          │                                        ║  │
│  ║  (Called by NLWeb tools)      ▼                                        ║  │
│  ║                                                                       ║  │
│  ║  NLWeb's retriever.py → our custom retrieval backend:                 ║  │
│  ║                                                                       ║  │
│  ║  1. Dense search (embeddings) → semantic similarity                   ║  │
│  ║  2. Sparse search (BM25) → keyword matching                          ║  │
│  ║  3. KG traversal → structural relationships                          ║  │
│  ║  4. Temporal filter → LLM-inferred time range pruning                ║  │
│  ║  5. Reciprocal Rank Fusion → merge all result sets                   ║  │
│  ║                                                                       ║  │
│  ║  Returns: ranked Schema.org objects with scores                       ║  │
│  ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                 │                                          │
│  ╔══════════════════════════════╪════════════════════════════════════════╗  │
│  ║  STAGE 3: READING            ▼                                        ║  │
│  ║  (NLWeb ranking.py + post_ranking.py)                                 ║  │
│  ║                                                                       ║  │
│  ║  NLWeb's ranking pipeline handles this natively:                      ║  │
│  ║  • Each retrieved item scored by LLM (with snippet generation)        ║  │
│  ║  • Post-ranking: summarize/generate mode applies Chain-of-Note        ║  │
│  ║  • mode=list → ranked items with scores                               ║  │
│  ║  • mode=summarize → summary + ranked items                            ║  │
│  ║  • mode=generate → RAG-style answer synthesis                         ║  │
│  ║                                                                       ║  │
│  ║  We extend with:                                                      ║  │
│  ║  • Knowledge update resolution (prefer most recent for conflicts)     ║  │
│  ║  • Abstention detection (no evidence → "I don't know")               ║  │
│  ║  • Cross-source evidence synthesis (Chain-of-Note)                    ║  │
│  ╚═══════════════════════════════════════════════════════════════════════╝  │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              PROFILING ENGINE                                                │
│              (Custom NLWeb Tools)                                            │
│                                                                             │
│  Registered in tools.xml as NLWeb-native tools:                             │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  PROFILE SEARCH TOOL                                                 │   │
│  │  ─────────────────────                                               │   │
│  │  Handles: "What are Theo's skills?" / "Tell me about Theo"          │   │
│  │  Action: Vector search → rank → return Schema.org PersonProfile      │   │
│  │  Returns: {"@type": "Person", "knowsAbout": [...], ...}             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  MEMORY QUERY TOOL                                                   │   │
│  │  ────────────────────                                                │   │
│  │  Handles: "What did Theo say about pricing in January?"             │   │
│  │  Action: Time-aware retrieval → Chain-of-Note synthesis             │   │
│  │  Tests: IE, TR, KU abilities from LongMemEval                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  PATTERN ANALYSIS TOOL                                               │   │
│  │  ──────────────────────                                              │   │
│  │  Handles: "What patterns do you see in Theo's data?"                │   │
│  │  Action: KG traversal + temporal windowing → cross-domain patterns  │   │
│  │  Output:                                                             │   │
│  │    Single-domain: "Spending up 14% over 6 months"                   │   │
│  │    Cross-domain:  "After heavy work weeks, delivery spending 3x"    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  DIMENSION SCORING TOOL                                              │   │
│  │  ──────────────────────                                              │   │
│  │  Handles: "Score Theo's financial literacy" / "Show all stats"      │   │
│  │  Action: Aggregate from KG + vector DB → compute per PROFILING_MATH │   │
│  │  Output: {"@type": "Rating", "ratingValue": 6, "bestRating": 10,   │   │
│  │           "name": "Financial Literacy", "ratingExplanation": "..."}  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  SCENARIO PROJECTION TOOL                                            │   │
│  │  ────────────────────────                                            │   │
│  │  Handles: "What happens if trends continue?" / "Best case?"         │   │
│  │  Action: Extrapolate dimension scores → generate 1y/5y/10y paths    │   │
│  │  Output: Drift / Rebalance / Transformation scenarios + actions     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  COMPARISON TOOL                                                     │   │
│  │  ────────────────                                                    │   │
│  │  Handles: "Compare Theo vs Elon" (Ensemble Query pattern)           │   │
│  │  Action: Load both profiles → radar chart data → delta analysis     │   │
│  │  Output: Schema.org CompareAction with dimension-by-dimension data  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  ACTION RECOMMENDER TOOL                                             │   │
│  │  ───────────────────────                                             │   │
│  │  Handles: "What should Theo do this week?"                          │   │
│  │  Action: Current scores + patterns + selected scenario → actions    │   │
│  │  Output: Weekly action items with rationale tied to data patterns   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              OUTPUT / PRESENTATION                                           │
│                                                                             │
│  NLWeb returns Schema.org JSON → clients render as needed:                  │
│                                                                             │
│  ┌──────────────────────┐   ┌─────────────────────────────────────────┐    │
│  │  QUESTLINE UI        │   │  PROFILER COMPARISON                    │    │
│  │  (remixed.tsx)       │   │  (theo_vs_elon.html)                    │    │
│  │                      │   │                                         │    │
│  │  Consumes /ask with  │   │  Consumes /ask with                     │    │
│  │  mode=list for       │   │  Comparison Tool →                      │    │
│  │  patterns, scores    │   │  radar charts, bars,                    │    │
│  │                      │   │  delta cards                            │    │
│  │  mode=generate for   │   │                                         │    │
│  │  chat agent          │   │                                         │    │
│  └──────────────────────┘   └─────────────────────────────────────────┘    │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  MCP SERVER (built into NLWeb)                                       │   │
│  │                                                                      │   │
│  │  Any MCP client (Claude Desktop, Copilot, custom agents) can:       │   │
│  │  • list_tools → see all 7 profiling tools                           │   │
│  │  • call_tool("ask", {query: "Theo's financial health"})             │   │
│  │  • Get Schema.org JSON back                                          │   │
│  │                                                                      │   │
│  │  This means: any AI agent can query Theo's profile natively.        │   │
│  │  The profile becomes an MCP-accessible knowledge source.            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              EVALUATION (LongMemEval Benchmark)                              │
│                                                                             │
│  1. CONVERT porthon/data → LongMemEval timestamped sessions                │
│  2. GENERATE 500 questions across 5 ability types                          │
│  3. FEED sessions sequentially through NLWeb's /ask endpoint               │
│     (memory detection stores facts; subsequent queries retrieve them)       │
│  4. EVALUATE with evaluate_qa.py (GPT-4o judge)                           │
│  5. MEASURE:                                                                │
│     • QA Accuracy per ability (IE, MR, KU, TR, ABS)                       │
│     • Retrieval Recall@K and NDCG@K                                        │
│     • Profiling accuracy vs master_profile.json ground truth               │
│     • Response latency (NLWeb fast-track vs full pipeline)                 │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  EVALUATION QUESTIONS (examples from Theo's data)                    │   │
│  │                                                                      │   │
│  │  IE:  "How much did Theo charge for the brand identity project?"    │   │
│  │  MR:  "Compare Theo's pricing confidence in Jan vs April"           │   │
│  │  KU:  "What is Theo's current hourly rate?" (changed over time)     │   │
│  │  TR:  "What skill was Theo learning in May 2024?"                   │   │
│  │  ABS: "What car does Theo drive?" → "I don't know"                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## How NLWeb Fits: Layer by Layer

### 1. NLWeb as Protocol Layer (NEW)

NLWeb provides the **conversational interface protocol** — the `/ask` and `/mcp` endpoints that all clients use. This replaces building a custom API.

| NLWeb Component | Our Usage |
|----------------|-----------|
| `baseHandler.py` | Orchestrates query → tool selection → retrieval → response |
| `query_analysis/` | Decontextualizes multi-turn queries, detects memory requests |
| `retriever.py` | Connects to our Qdrant vector DB (NLWeb supports Qdrant natively) |
| `ranking.py` | LLM-based scoring of retrieved items |
| `post_ranking.py` | Summarize/generate modes for Chain-of-Note reading |
| `router.py` + `tools.xml` | Routes queries to our 7 custom profiling tools |
| `memory.py` | Detects facts to remember across sessions |
| `fastTrack.py` | Parallel optimistic path for simple profile lookups |
| `prompts.py` | XML-based prompts, specializable per data type |
| `/mcp` endpoint | Makes profile queryable by any MCP agent |

### 2. Schema.org as Data Format (NEW)

NLWeb's core insight: **Schema.org is the semantic layer**. All our data must be stored as Schema.org objects in the vector DB.

```json
// A memory entry in the vector DB
{
  "@type": "DataFeedItem",
  "@id": "c_0001",
  "dateCreated": "2024-01-18T23:00:00-05:00",
  "name": "Pricing anxiety discussion",
  "description": "USER: I undercharged a client again...",
  "keywords": ["freelance", "pricing", "confidence"],
  "sourceOrganization": "ai_chat",
  "additionalProperty": [
    {"@type": "PropertyValue", "name": "extracted_facts",
     "value": "Theo charges $600 for brand identity; has pricing anxiety"},
    {"@type": "PropertyValue", "name": "pii_level", "value": "synthetic"}
  ]
}
```

```json
// A profiling dimension score
{
  "@type": "Rating",
  "name": "Financial Literacy",
  "ratingValue": 6,
  "bestRating": 10,
  "worstRating": 0,
  "ratingExplanation": "Savings rate 18% — up from 12% six months ago",
  "additionalProperty": [
    {"@type": "PropertyValue", "name": "trend", "value": "up"},
    {"@type": "PropertyValue", "name": "previous_value", "value": 5}
  ]
}
```

### 3. Custom NLWeb Tools (NEW)

We register 7 tools in `tools.xml` that the NLWeb router selects from based on query intent:

| Tool | Trigger Queries | Backend |
|------|----------------|---------|
| Profile Search | "Who is Theo?" / "Theo's skills" | Vector DB search |
| Memory Query | "What did he say about..." | Time-aware retrieval + CoN |
| Pattern Analysis | "What patterns..." / "Why does..." | KG traversal + temporal |
| Dimension Scoring | "Score his..." / "Show stats" | KG aggregate + profiling math |
| Scenario Projection | "What if..." / "Best case" | Score extrapolation |
| Comparison | "Compare Theo vs..." | Multi-profile ensemble |
| Action Recommender | "What should he do..." | Scores + patterns → actions |

### 4. Memory Detection → Long-Term Storage (NEW)

NLWeb's `DetectMemoryRequestPrompt` becomes our **online memory indexing hook**:

```xml
<Prompt ref="DetectMemoryRequestPrompt">
  <promptString>
    Analyze the following interaction with the user.
    Does this interaction reveal personal information, preferences,
    life events, financial details, goals, or emotional states
    about the user that should be remembered for future interactions?
    Extract ALL implicit facts, not just explicit memory requests.
    The interaction is: {request.rawQuery}.
  </promptString>
  <returnStruc>
    {
      "facts_detected": ["fact1", "fact2", ...],
      "should_update_kg": "True or False",
      "kg_updates": [{"entity": "...", "relation": "...", "value": "..."}]
    }
  </returnStruc>
</Prompt>
```

This is the **key integration point**: every query through NLWeb automatically triggers memory extraction → indexing into both Vector DB and KG.

### 5. NLWeb's Fast Track = Our Profiling Cache

For common queries like "Show Theo's stats" or "What are his scores?", the fast-track path serves pre-computed profiling results from cache, bypassing the full retrieval pipeline. Only novel or temporal queries go through the full 3-stage memory pipeline.

---

## Data Flow (Revised)

```
porthon/data/*.jsonl
       │
       ▼
[Schema.org Transform] ── convert to DataFeedItem objects
       │
       ▼
[LongMemEval Indexing] ── decompose → fact-augment → timestamp
       │                │
       ▼                ▼
[Qdrant Vector DB]  [Neo4j Knowledge Graph]
       │                │
       ▼                ▼
[NLWeb retriever.py] ← connects to both stores
       │
       ▼
[NLWeb Handler Pipeline]
  │  decontextualize → tool select → retrieve → rank → respond
  │
  ├─ /ask  → JSON (Schema.org) → Questline UI / Profiler HTML
  ├─ /mcp  → MCP protocol → Claude Desktop / Copilot / agents
  │
  └─ Memory Detection → new facts indexed back into stores
```

---

## Implementation Plan

### Phase 1: NLWeb + Qdrant Setup
1. Fork NLWeb, configure Qdrant as vector store
2. Ingest porthon/data as Schema.org DataFeedItem objects
3. Run fact-augmented key expansion during ingestion
4. Verify basic `/ask` queries work against Theo's data

### Phase 2: Custom Tools
5. Implement 7 profiling tools in `tools.xml` + Python handlers
6. Connect profiling math (PROFILING_MATH.md) to Dimension Scoring tool
7. Implement KG (Neo4j) population from extracted facts
8. Add KG traversal to Pattern Analysis tool

### Phase 3: Memory Pipeline
9. Customize `DetectMemoryRequestPrompt` for implicit fact extraction
10. Implement knowledge update resolution (UPDATED_TO edges in KG)
11. Add temporal query expansion per LongMemEval paper
12. Test multi-session memory across sequential NLWeb calls

### Phase 4: Output Integration
13. Wire Questline UI to consume NLWeb `/ask` responses
14. Wire Profiler Comparison HTML to use Comparison tool
15. Expose `/mcp` endpoint for agent access

### Phase 5: LongMemEval Evaluation
16. Convert porthon data → LongMemEval session format
17. Generate evaluation questions for Theo's data
18. Run benchmark through NLWeb pipeline
19. Report accuracy, recall, latency metrics

---

## Why This Architecture

| Decision | Rationale |
|----------|-----------|
| **NLWeb as interface** | Don't build a custom API — get REST + MCP + streaming + Schema.org for free. Microsoft-backed, MIT licensed. |
| **Schema.org data format** | NLWeb's LLMs understand Schema.org natively. Our data becomes interoperable with 100M+ websites. |
| **NLWeb tools = profiling tools** | The tool router pattern is exactly what we need — different query intents map to different profiling capabilities. |
| **Memory detection hook** | NLWeb already has the pre-retrieval memory prompt. We extend it for implicit fact extraction (LongMemEval's key insight). |
| **Fast-track caching** | Profile scores don't change every query. NLWeb's fast-track path avoids redundant retrieval for common lookups. |
| **MCP native** | Any AI agent can query the profile. The profile becomes a tool, not just a dashboard. |
| **Qdrant** | NLWeb supports it natively. No adapter needed. |
| **Dual store preserved** | Vector DB for semantic retrieval (NLWeb native), KG for structural profiling (custom tool). Both needed. |
