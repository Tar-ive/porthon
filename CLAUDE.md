# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: Questline

AI agent that analyzes behavioral data (financial, calendar, social, lifelog) to project life scenarios 1/5/10 years out and generate concrete daily micro-actions. Built for a hackathon demo using a synthetic persona dataset (`data/all_personas/`). Primary demo persona is **Theo Nakamura (p05)**.

## Commands

```bash
# Install all dependencies
make install

# Build frontend and copy to backend, then start server at http://localhost:8000
make dev

# Build only (frontend → backend/assets/)
make build

# Frontend only
cd src/frontend && pnpm dev        # dev server
cd src/frontend && pnpm build      # production build

# Backend only
cd src/backend && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Add backend dependency
cd src/backend && uv add <package>

# Add frontend dependency
cd src/frontend && pnpm add <package>

# Run tests
make test              # Fast tests (default, no external services)
make test-live         # Live integration tests (requires API keys)
make test-live-kg      # Live KG tests (requires Neo4j/Qdrant + binding keys)
```

## Architecture

Three-step agent pipeline — each step receives **typed structured JSON**, not raw file dumps:

1. **Structured Extractor** (deterministic Python) — parses `.jsonl` data files into compact typed time-series structs. Must stay under ~8k tokens of LLM input per step.
2. **Pattern Analyzer** (Claude tool-use, Agent Step 1) — outputs `PatternReport` with `{ id, trend, domains, confidence, data_refs, is_cross_domain }`. Must produce ≥2 cross-domain patterns per persona.
3. **Scenario Generator** (Agent Step 2) — takes `PatternReport` + persona goals, outputs `ScenarioSet` with 3 scenarios (`1yr/5yr/10yr`, likelihood: `most_likely/possible/aspirational`). Each scenario must reference pattern ids.
4. **Action Planner** (Agent Step 3) — takes selected scenario + live calendar/transaction data, outputs `ActionPlan` with 3–5 time-bound actions. Each action must cite a specific `data_ref` record.

Typed contracts are defined in code — see `PRD.md` for the full struct definitions.

**Key constraint:** Each agent step has a 30-second timeout with graceful error state. Streaming output during each step is required (no blank loading screens).

## Deep Agents

The system uses "workers" that run in an always-on master loop:

| Worker | Purpose |
|--------|---------|
| **KgWorker** | Knowledge Graph memory, pattern recognition |
| **CalendarWorker** | Calendar focus blocks, body-doubling windows |
| **NotionLeadsWorker** | Lead tracking in Notion |
| **NotionOpportunityWorker** | Opportunity pipeline in Notion |
| **FigmaWorker** | Design challenges, portfolio scaffolding |
| **FacebookWorker** | Social media drafting |

Core orchestration:
- **Master Loop** (`deepagent/loop.py`) — Always-on, 15-minute tick + event-triggered cycles
- **Dispatcher/Factory** (`deepagent/dispatcher.py`, `factory.py`) — Worker lifecycle management

See `docs/product_concept.md` for allowed vs never actions (auto-execute vs approval-required).

## Frontend Flow

4 screens: **Consent → Patterns/Stats → Scenarios → Actions**

- Consent screen uses `consent.json` schema; toggling a source excludes it from the entire pipeline
- Pattern screen: 3–7 patterns, cross-domain ones visually distinguished, data_refs visible on expand
- Stats dashboard: 5 stats (financial health, physical activity, social engagement, career momentum, relationship quality), scored 1–10, derived from data not hardcoded
- Scenario screen: select one scenario to trigger Action Planner
- Actions screen: each action links rationale to a specific pattern and data record

## Test Types

| Type | Location | When to Run |
|------|----------|-------------|
| **fast** | `src/backend/tests/fast/` | Default — no external services needed |
| **live** | `src/backend/tests/live/` + `test_e2e_composio.py` | Requires API keys (Composio, Figma, etc.) |
| **KG live** | `tests/live/test_live_kg.py` | Requires Neo4j/Qdrant + API keys |

**Rule:** Run `make test` before every commit. Run `make test-live` before merging to main.

## Slice Pattern

3-slice delivery with test gates — see `docs/SLICED_EXECUTION_PLAN.md`:

- **Slice 1**: Foundation Shell + Read-Only Agent Map
- **Slice 2**: Always-On Loop + Scenario Activation + Queue Dispatch
- **Slice 3**: Skills + Tiered Approval + Realtime Stream

**Policy:** Do not progress to next slice until current slice test gate passes.

## Data Layout

```
data/all_personas/
  p05/                        # Theo Nakamura — primary demo persona
    persona_profile.json
    consent.json
    lifelog.jsonl
    conversations.jsonl
    emails.jsonl
    calendar.jsonl
    social_posts.jsonl
    transactions.jsonl
    files_index.jsonl
```

## API Design Best Practices

All API endpoints follow Stripe-like conventions for agent consumption:

### Resource Identity
- Resource IDs are prefixed: `scen_` (scenario), `qst_` (quest), `apprv_` (approval), `evt_` (event), `msg_` (message), `wrkr_` (worker)
- Agents can infer resource type from the prefix without making an API call

### Safety & Idempotency
- All mutating operations (`POST`, `PUT`, `DELETE`) require an `Idempotency-Key` header
- Prevents duplicate actions on network retries

### Data Fetching
- Use `expand[]` query param to reduce N+1 requests: `GET /v1/quests/qst_xxx?expand[]=scenario`
- Default returns IDs only; expansion includes full nested objects

### Pagination
- Cursor-based only: `starting_after` + `has_more` (no offset)
- Pass last item's ID to `starting_after` for next page

### Error Format
```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "resource_missing",
    "message": "The requested scenario does not exist.",
    "param": "scenario_id",
    "doc_url": "https://api.porthon.ai/docs/errors"
  }
}
```

### Extensibility
- All resources support a `metadata` key-value store for custom state
- Pin API version via header: `X-Api-Version: 2026-03-01`

See `docs/api_design_spec.md` for full specification.

## Serving

FastAPI serves the Vite SPA via `StaticFiles(html=True)` mounted at `/`. API routes must be defined **before** the static mount. Vite builds assets to `static/` subdirectory (not `assets/`) — configured in `vite.config.ts`.

## Build Priority

Ship in order: P0 (Extractor + 3-step pipeline + streaming UI) → P1 (consent wiring + cross-domain insights + data refs on expand) → P2 (stats dashboard + compound summaries) → P3 (RPG map visualization, stretch).
