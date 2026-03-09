# Questline

**Track 2 — AI Companions**

An AI agent that reads your behavioral data — calendar, finances, mood logs, social posts — discovers cross-domain patterns in your life, and generates personalized 1/5/10-year life scenarios with concrete daily micro-actions to make them real.

Demo persona: **Theo Nakamura (p05)** — freelance creative/barista in Austin, ADHD, undercharging, burning out.

---

## Demo Walkthrough

1. **Ingest** — Load data sources and construct personalized knowledge graph
2. **Patterns** — AI surfaces cross-domain behavioral patterns (e.g. "Burnout Cascade": when Theo's meetings exceed 30h/week, his exercise drops and food delivery spend triples)
3. **Questlines** — Choose from 3 life trajectory scenarios across 1yr / 5yr / 10yr horizons
4. **Actions** — 5–10 time-bound micro-actions, each citing the specific data record it's based on
5. **Chat** — Conversational follow-up with voice input (Whisper)

---

## Team

| Name | Role |
|------|------|
| Michael Samon | Frontend, UX, Infrastructure |
| Kusum Sharma | Backend, Data Design |
| Saksham Adhikari| Agent, External Integrations |

---

## Why Track 2?

Questline is a companion that knows your whole life — not just your tasks, not just your calendar, not just your bank account. It connects the dots across all of them to show you patterns you can't see from any one app. The "Burnout Cascade" pattern Theo's agent discovers — where packed meeting weeks cause exercise to collapse and food delivery spend to spike — is only visible when you look at calendar + lifelog + finance together. Questline's job is to catch those loops before they compound, and give you a concrete path out.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4 |
| Backend | FastAPI (Python 3.13), uvicorn |
| LLM | Anthropic Claude (pattern analysis, scenario generation, action planning) |
| Voice | OpenAI Whisper (transcription) |
| Knowledge Graph | LightRAG + Neo4j + Qdrant |
| Integrations | Composio (Notion, Google Calendar, Figma) |
| Data | Synthetic JSONL persona dataset |

### Architecture

```
JSONL Persona Data
    ↓
[1] Extractor (deterministic Python) — parses data into typed structs, <8k tokens
    ↓
[2] Pattern Analyzer (Claude LLM) — outputs PatternReport with cross-domain correlations
    ↓
[3] Scenario Generator (Claude LLM) — 1yr/5yr/10yr scenarios, referenced to pattern IDs
    ↓ (user selects scenario)
[4] Action Planner (Claude LLM) — 3–5 time-bound actions, each cites a specific data_ref
    ↓
[5] Agent Workers (always-on) — CalendarWorker, NotionWorker, FigmaWorker deploy actions live
```

Each step has a 30-second timeout with graceful fallback. Responses stream in real-time (no blank loading screens). Analysis is hash-cached — unchanged data skips LLM calls entirely.

---

## Environment Variables

```bash
# LLM (OpenRouter or any OpenAI-compatible endpoint)
LLM_BINDING=openai
LLM_BINDING_API_KEY=sk-or-...
LLM_BINDING_HOST=https://openrouter.ai/api/v1
LLM_MODEL=x-ai/grok-4.1-fast

# Embedding (OpenAI)
EMBEDDING_BINDING_API_KEY=sk-proj-...
EMBEDDING_BINDING_HOST=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-large

# Neo4j (Aura or self-hosted)
NEO4J_URI=neo4j+s://<instance>.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=

# Qdrant (cloud or self-hosted)
QDRANT_URL=https://<cluster>.qdrant.io
QDRANT_API_KEY=

# Notion
NOTION_INTEGRATION_SECRET=
NOTION_ROOT_PAGE_ID=

# Figma
FIGMA_API_KEY=
FIGMA_CLIENT_ID=
FIGMA_CLIENT_SECRET=

# Composio (Notion, Calendar, Figma integrations)
COMPOSIO_API_KEY=

# Auth
PORTTHON_API_KEYS=sk_live_ops_<your_key>
PORTTHON_SESSION_SECRET=<random_secret>
```

See `.env.example` for the full list including LightRAG, Redis, and all connection pool settings. The app works without Composio/Neo4j/Qdrant — switch to local fallbacks in `.env.example` comments and agent deployment features will be disabled but the core pipeline runs.

---

## Datasets

All data is **synthetic**, generated for this hackathon. No real personal data is used.

| File | Records | Description |
|------|---------|-------------|
| `persona_profile.json` | 1 | Goals, ADHD context, creative tech stack |
| `consent.json` | 1 | Per-domain opt-in schema |
| `lifelog.jsonl` | 150 | Mood, energy, events, daily logs |
| `calendar.jsonl` | 80 | Coffee shop shifts, client calls, skate days |
| `transactions.jsonl` | 120 | Rent, CC payments, client invoices, subscriptions |
| `social_posts.jsonl` | 50 | Instagram/LinkedIn (portfolio, freelance tips) |
| `emails.jsonl` | 80 | Client threads, invoices, roommates |
| `conversations.jsonl` | 8 | Prior AI sessions on pricing, ADHD, business dev |

Data lives in `data/all_personas/persona_p05/`.

---

## Project Quick Start

```bash
# Install all dependencies
make install

# Build frontend + start server at http://localhost:8000
make dev
```

Copy `.env.example` to `.env` and fill in your API keys (see [Environment Variables](#environment-variables)).

## How to Reproduce the Demo

```bash
make dev
# Open http://localhost:8000
# Click through: Consent → Patterns → Questlines → Actions
# Try the chat with the mic button for voice input
```

The demo uses a pinned test token (`sk_demo_default`) that locks to persona p05 with `temperature: 0` for deterministic output.

To run tests:

```bash
make test          # Fast tests, no external services needed
make test-live     # Integration tests (requires API keys)
```

---

## Known Limitations & Next Steps

**Known Limitations**
- Single persona only (Theo / p05) — multi-user auth not implemented
- Agent workers (Notion, Figma, Calendar) require Composio setup and won't run in demo mode
- Knowledge Graph features (Neo4j/Qdrant) require local services; app falls back to in-memory patterns without them
- Pattern analysis can take 10–20 seconds on cold start (no cache)

**Next Steps**
- More data connectors (Plaid, Google Calendar OAuth, Instagram API)
- Multi-user support with per-user consent and data isolation
- Approval queue UI for human-in-the-loop action review
- Mobile app with push notifications for daily action reminders
- Longitudinal tracking: did following the actions actually change the trajectory?
