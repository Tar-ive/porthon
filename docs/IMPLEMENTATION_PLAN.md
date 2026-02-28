# Implementation Plan: Hyperpersonalized Agent with Web UI

**Date:** 2026-02-28  
**Goal:** A web-accessible chat agent that retrieves from a personal KG (Neo4j + Qdrant) and responds with deep personalization via profiler-enhanced SOUL.md and USER.md.

---

## Simplified Architecture

```
Browser (Web UI)
    │ WebSocket / HTTP
    ▼
FastAPI Server
    │
    ├── Chat endpoint (/chat)
    │       │
    │       ├── 1. Classify intent (needs KG? what mode?)
    │       ├── 2. If needed: query LightRAG (Neo4j + Qdrant)
    │       ├── 3. Inject profile context + retrieved data into prompt
    │       ├── 4. LLM generates response (personality from SOUL.md)
    │       └── 5. Return response (streamed)
    │
    ├── SOUL.md  (agent personality, generated from profiler)
    ├── USER.md  (user model, generated from KG + profiler)
    └── LightRAG instance (Neo4j graph + Qdrant vectors)
```

---

## What the Agent Knows and When It Fetches

### The Decision Tree (Every Message)

```
User message arrives
    │
    ├─ Does it reference specific data? (money, dates, events, tools, people)
    │   YES → LightRAG query (mode="mix") — entities + relationships + chunks
    │
    ├─ Does it ask about patterns, habits, or trends?
    │   YES → LightRAG query (mode="global") — relationship-centric traversal
    │
    ├─ Does it ask for advice or "should I..."?
    │   YES → LightRAG query (mode="hybrid") + inject profiler scores
    │
    ├─ Is it emotional / venting / casual?
    │   YES → No KG fetch. Respond from SOUL.md personality only.
    │         (But use USER.md context for empathetic grounding)
    │
    └─ Ambiguous?
        → Default to mode="local" (light entity lookup, fast)
```

### What Gets Injected Into the Prompt

| Source | Always Loaded | Fetched Per-Query |
|--------|:---:|:---:|
| SOUL.md (personality, tone, modifiers) | ✅ | |
| USER.md (identity, goals, patterns, preferences) | ✅ | |
| Profiler scores (archetype, dimensions, deltas) | ✅ (cached) | |
| KG entities + relationships | | ✅ when relevant |
| Raw text chunks (original JSONL excerpts) | | ✅ when grounding needed |

---

## Agent Personality: Smart Communication

The SOUL.md encodes these linguistic behaviors:

### Mirroring
- Echo the user's vocabulary and phrasing style back to them
- If they say "I'm crushed" → don't say "I understand you're disappointed" → say "yeah, that's crushing"
- Match energy level: short messages get short replies, detailed questions get detailed answers

### Pattern Recognition (Spoken Aloud)
- When the agent retrieves a KG pattern, it names it naturally:
  - "This is the third time you've mentioned undercharging — there's a pattern here"
  - "Your calendar says learning but your revenue says conversion is the bottleneck"
- Never quotes profiler scores directly. Translates them into human language.

### Linguistic Rules (Encoded in SOUL.md)
```markdown
## Communication Style
- Mirror their words. If they say "freaking out" say "freaking out", not "experiencing anxiety"
- Match message length to theirs. Short begets short.
- Name patterns when you see them, but only once. Don't lecture.
- Use "I notice..." not "The data shows..."
- When giving advice: one concrete action, not a list of five
- For ADHD users: bold the single most important thing. Everything else is context.
- Never say "based on your profile" or "according to the knowledge graph"
- Just know things. Like a friend who pays attention.
```

---

## Implementation Phases

### Phase 1: Infrastructure Setup
**Goal:** Neo4j + Qdrant running on the cloud, LightRAG configured, data ingested and stored in cloud.
- [ ] Configure LightRAG with Neo4j (`Neo4JStorage`) + Qdrant (`QdrantVectorDBStorage`)
- [ ] Write `scripts/ingest.py` — reads all `data/*.jsonl` + `persona_profile.json`, feeds to `LightRAG.ainsert()` -> understand what is in cloud, try and test with python -m pytest tests/test_qdrant_migration.py tests/test_dimension_mismatch.py -v and python -m pytest tests/test_neo4j_fulltext_index.py -v --run-integration, try to retrieve queries data and relationships from cloud neo4j and qdrant. 
.env                        # NEO4J_URI, QDRANT_URL, API keys and other required .env files  -> /home/sadhikari/porthon/LightRAG/.env
```

### Phase 2: Profile Generation
**Goal:** SOUL.md and USER.md auto-generated from profiler + KG data.

- [ ] Write `scripts/generate_profile.py`:
  1. Load `data/summaries/master_profile.json`
  2. Run `CrossPlatformProfiler` → get scores, archetype, deltas
  3. Query Neo4j for top entities by degree (centrality)
  4. Generate `agent/SOUL.md` from archetype + dimension scores + deltas
  5. Generate `agent/USER.md` from profile + KG entity summary
- [ ] Review and hand-tune the generated files

**Key files:**
```
scripts/generate_profile.py
agent/SOUL.md               # Generated
agent/USER.md               # Generated
```

### Phase 3: Agent Backend
**Goal:** FastAPI server that handles chat with KG-aware retrieval.

- [ ] `agent/server.py` — FastAPI app with:
  - `POST /chat` — accepts message, returns streamed response
  - `GET /health` — status check
  - WebSocket `/ws` — for real-time streaming
- [ ] `agent/retriever.py` — wraps LightRAG query with intent classification:
  ```python
  async def retrieve_context(query: str, rag: LightRAG) -> str | None:
      """Decide if/how to query KG, return formatted context or None."""
      intent = classify_intent(query)  # keyword rules + optional LLM
      if intent == "casual":
          return None
      mode = {"factual": "mix", "pattern": "global", 
              "advice": "hybrid", "recall": "local"}[intent]
      result = await rag.aquery(query, param=QueryParam(mode=mode))
      return result
  ```
- [ ] `agent/prompt_builder.py` — assembles system prompt:
  ```python
  def build_prompt(soul: str, user: str, context: str | None) -> str:
      prompt = f"{soul}\n\n{user}"
      if context:
          prompt += f"\n\n## What I Found\n{context}"
      return prompt
  ```
- [ ] Intent classifier — write prompt for LLM classifier based on prompts from -> - Entity extraction prompts: `LightRAG/lightrag/prompt.py` + what the agent knows about the person (profiling maths at play(deterministic test cases))
  ```python
  FACTUAL_TRIGGERS = ["how much", "when did", "what did I spend", "last month"]
  PATTERN_TRIGGERS = ["pattern", "notice", "trend", "always", "keep doing"]
  ADVICE_TRIGGERS = ["should I", "what do you think", "is it worth"]
  
  def classify_intent(query: str) -> str:
      q = query.lower()
      if any(t in q for t in FACTUAL_TRIGGERS): return "factual"
      if any(t in q for t in PATTERN_TRIGGERS): return "pattern"
      if any(t in q for t in ADVICE_TRIGGERS): return "advice"
      return "casual"
  ```

**Key files:**
```
agent/server.py             # FastAPI app
agent/retriever.py          # KG query orchestration
agent/prompt_builder.py     # System prompt assembly
agent/intent.py             # Intent classification
requirements.txt            # fastapi, uvicorn, lightrag, neo4j, qdrant-client
```

### Phase 4: Web UI
**Goal:** Clean chat interface in the browser.

- [ ] Single-page React app (or plain HTML + JS for simplicity)
- [ ] WebSocket connection to FastAPI for streaming responses
- [ ] Features:
  - Chat bubbles with markdown rendering
  - Typing indicator during LLM generation
  - Message history (session-based, in-memory)
  - Sidebar showing which KG entities were retrieved (debug mode)
  - Tool calls showing bubbles with json rendering 

**Key files:**
```
web/
├── index.html              # Single-page chat UI
├── style.css               # Styling
└── app.js                  # WebSocket client, message rendering
```

Minimal approach — a single `index.html` served by FastAPI's static files:
```python
# In server.py
app.mount("/", StaticFiles(directory="web", html=True))
```

### Phase 5: Polish & Feedback Loop
- [ ] Conversation logging → `memory/YYYY-MM-DD.md` 
- [ ] Periodic re-ingestion of new conversations into LightRAG
- [ ] SOUL.md/USER.md refresh when profile shifts detectably
- [ ] Test edge cases: empty KG results, ambiguous queries, long conversations

---

## Folder Structure (Final)

```
porthon/
├── agent/
│   ├── server.py            # FastAPI backend
│   ├── retriever.py         # KG retrieval orchestration
│   ├── prompt_builder.py    # Prompt assembly
│   ├── intent.py            # Intent classifier
│   ├── SOUL.md              # Auto-generated personality
│   └── USER.md              # Auto-generated user model
├── web/
│   ├── index.html           # Chat UI
│   ├── style.css
│   └── app.js
├── scripts/
│   ├── ingest.py            # Data → LightRAG → Neo4j + Qdrant
│   └── generate_profile.py  # Profiler → SOUL.md + USER.md
├── data/                    # Raw JSONL (existing)
├── profiler.py              # CrossPlatformProfiler (existing)
├── LightRAG/                # RAG framework (existing)
├── docker-compose.yml       # Neo4j + Qdrant services
├── requirements.txt
└── docs/
    ├── AGENT_ARCHITECTURE.md   # Deep research doc
    └── IMPLEMENTATION_PLAN.md  # This file
```

---

## Success Criteria

1. **Open browser → chat with agent → agent responds in character** (SOUL.md personality)
2. **Ask "what did I spend on subscriptions?"** → agent queries KG, returns accurate data from transactions
3. **Ask "do you notice any patterns?"** → agent walks relationships in Neo4j, names patterns naturally
4. **Ask "should I take a $30/hr client?"** → agent uses profiler context (undercharging pattern, financial stress score) to give personalized advice without quoting numbers
5. **Say "I'm overwhelmed"** → agent responds with empathy, mirrors language, doesn't dump data
