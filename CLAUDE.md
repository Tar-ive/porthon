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
```

## Architecture

Three-step agent pipeline — each step receives **typed structured JSON**, not raw file dumps:

1. **Structured Extractor** (deterministic Python) — parses `.jsonl` data files into compact typed time-series structs. Must stay under ~8k tokens of LLM input per step.
2. **Pattern Analyzer** (Claude tool-use, Agent Step 1) — outputs `PatternReport` with `{ id, trend, domains, confidence, data_refs, is_cross_domain }`. Must produce ≥2 cross-domain patterns per persona.
3. **Scenario Generator** (Agent Step 2) — takes `PatternReport` + persona goals, outputs `ScenarioSet` with 3 scenarios (`1yr/5yr/10yr`, likelihood: `most_likely/possible/aspirational`). Each scenario must reference pattern ids.
4. **Action Planner** (Agent Step 3) — takes selected scenario + live calendar/transaction data, outputs `ActionPlan` with 3–5 time-bound actions. Each action must cite a specific `data_ref` record.

Typed contracts are defined in code — see `PRD.md` for the full struct definitions.

**Key constraint:** Each agent step has a 30-second timeout with graceful error state. Streaming output during each step is required (no blank loading screens).

## Frontend Flow

4 screens: **Consent → Patterns/Stats → Scenarios → Actions**

- Consent screen uses `consent.json` schema; toggling a source excludes it from the entire pipeline
- Pattern screen: 3–7 patterns, cross-domain ones visually distinguished, data_refs visible on expand
- Stats dashboard: 5 stats (financial health, physical activity, social engagement, career momentum, relationship quality), scored 1–10, derived from data not hardcoded
- Scenario screen: select one scenario to trigger Action Planner
- Actions screen: each action links rationale to a specific pattern and data record

## Data Layout

```
data/all_personas/
  p01/                        # Jordan Lee — primary demo persona
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

## Serving

FastAPI serves the Vite SPA via `StaticFiles(html=True)` mounted at `/`. API routes must be defined **before** the static mount. Vite builds assets to `static/` subdirectory (not `assets/`) — configured in `vite.config.ts`.

## Build Priority

Ship in order: P0 (Extractor + 3-step pipeline + streaming UI) → P1 (consent wiring + cross-domain insights + data refs on expand) → P2 (stats dashboard + compound summaries) → P3 (RPG map visualization, stretch).
