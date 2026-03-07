# Real-Time Demo — Current State & Changes

**Branch:** `milestone1_kusum`
**Date:** 2026-03-06

---

## What the demo shows

Questline is an AI life-scenario agent for Theo Nakamura (persona p05). The core demo narrative is:

> "Your data changes in real time. The daemon detects it instantly, re-runs analysis, and updates your life trajectories — all without you doing anything."

The UI makes this visible end-to-end: push a scripted data event → watch the daemon process it → see trajectories refresh live.

---

## System architecture (relevant to the demo)

```
Browser (SSE)
    │
    ├── /api/agent/stream       ← useAgentStream hook (analysis events)
    └── /v1/events/stream       ← TelemetryFeed (raw event log)

Backend
    ├── DataWatcher             ← polls persona JSONL files every 3s
    │     └── force_check(demo_mode)  ← triggered by demo push
    ├── AnalysisCache           ← incremental, skips LLM if inputs unchanged
    │     ├── get_scenarios(has_llm)
    │     └── get_actions(has_llm)
    └── AlwaysOnMaster          ← 15-min tick + event-triggered loop
          └── StreamBroker      ← SSE fan-out to all subscribers
```

---

## Demo data events (4 scripted pushes)

| Slug | Domain | What it adds |
|---|---|---|
| `01_high_value_client` | calendar | NovaBit startup discovery call — $150/hr motion design retainer |
| `02_debt_milestone` | finance | $1k debt payoff, balance drops to $2,640 |
| `03_motion_reel_viral` | social | Motion reel hits 50k views, 12 inbound DMs |
| `04_agency_partnership` | lifelog | ATX Creative Co offers $3k/month retainer |

Push via UI (DemoFeed panel) or manually:
```bash
curl -X POST http://localhost:8000/api/agent/demo/push/01_high_value_client
```

---

## SSE event sequence on a demo push

1. `data_changed` — immediately, domain + source=demo_push
2. `analysis_running` — stage: scenarios, message describing the domain
3. `scenarios_updated` — count: 3 (new trajectories ready)
4. `analysis_running` — stage: actions (if a scenario is active)
5. `actions_updated` — count: N (quest recommendations refreshed)

---

## Frontend components

### New components (added this session)

#### `DaemonBar.tsx`
Slim persistent status bar rendered below the scenario title in `MissionControl`.

- **Idle:** `● Daemon running · AlwaysOnMaster · 15 min tick + event-triggered`
- **Analyzing:** bar turns amber, pulsing dot, shows analysis message from SSE
- **Updated:** bar turns green for 2.5s, shows "Trajectories updated" + timestamp
- Connected via `useAgentStream` hook

#### `DemoFeed.tsx`
Panel in the MissionControl sidebar with 4 clickable event cards.

- Loads event list from `GET /api/agent/demo/events`
- Click → `POST /api/agent/demo/push/{slug}`
- Card states: `idle → pushing → analyzing → done`
- Badge in header shows "analyzing domain…" while SSE signals running, "↻ trajectories updated" on completion
- Tracks active slug via `useAgentStream` `scenariosVersion` / `isAnalyzing`

#### Updated `TelemetryFeed.tsx`
Now shows human-readable event descriptions instead of raw key=value dumps.

- Color coding: amber for data_changed, yellow for analysis_running, green for updated/done, red for errors
- Each event type maps to a glyph + label + description derived from payload
- For `data_changed`: distinguishes demo_push vs file_poll source
- For `scenarios_updated`: shows count of regenerated trajectories

#### Updated `OpsNavbar.tsx`
Adds a live daemon status indicator to the Dashboard navbar (mirrors DaemonBar for the `/` route).

- Pulsing green dot → amber during analysis → green flash on update
- Label: "daemon running" / "analyzing…" / "updated"
- Connected via `useAgentStream`

### Existing components (unchanged behavior, visible in demo)

| Component | What it shows |
|---|---|
| `ScenarioSelect.tsx` | Live banner when `data_changed` fires; auto-refetches when `scenariosVersion` increments |
| `WorkerFleet.tsx` | 6 always-on workers (KG, Calendar, Notion×2, Figma, Facebook); SSE-refreshed |
| `ApprovalQueue.tsx` | Pending agent approvals; approve/reject inline |
| `AnimatedKnowledgeGraph.tsx` | Animated KG visualization |
| `Chat.tsx` | Agent chat with streaming; auto-refreshes quests on `actionsVersion` |

---

## Backend changes (this session)

### `daemon/watcher.py` — Mode-aware execution context

Added `RunContext` dataclass:
```python
@dataclass
class RunContext:
    demo_mode: bool = False   # controls reasoning mode only
    source: str = "file_poll" # demo_push | live_webhook | file_poll | manual
    notion_write: bool = True # Notion writes always allowed
```

Key behavior changes:
- `force_check(demo_mode=False)` — explicit mode instead of inferred from env
- `has_llm = env_has_llm and not ctx.demo_mode` — demo pushes force demo reasoning even when live LLM keys exist
- KG ingest (`_ingest_new_record`) skipped when `demo_mode=True` — prevents demo data mutating live LightRAG
- `data_changed` SSE event now includes `source` field

**Why:** Live KG updates take 2-3 minutes per record. Demo mode uses fast pre-computed scenarios while keeping Notion writes and live webhook visibility intact.

### `app/api/routes_agent.py` — Demo push passes mode

```python
# Before
asyncio.create_task(watcher.force_check())

# After
asyncio.create_task(watcher.force_check(demo_mode=True))
```

### `deepagent/workers/kg_worker.py` — Hardened config validation

`_create_rag_instance()` now requires all three:
- `NEO4J_URI`
- `LLM_BINDING_API_KEY` or `OPENAI_API_KEY`
- `EMBEDDING_BINDING_API_KEY` or `OPENAI_API_KEY`

Partial config (Neo4j set but no LLM key) now logs one clean warning and returns `None` instead of reaching LightRAG internals and throwing `NoneType.__aexit__` errors.

---

## Reasoning mode vs integration mode

The watcher separates these two concerns:

| Concern | Demo push | Live poll / webhook |
|---|---|---|
| Reasoning (LLM/KG) | demo mode (fast, pre-computed) | live if keys configured |
| KG ingest | skipped | runs if NEO4J + LLM + embedding keys present |
| Notion writes | allowed | allowed |
| Webhook events visible | yes | yes |
| SSE events emitted | yes | yes |

This means a demo push can still trigger real Notion side effects (leads, opportunities) while keeping the analysis fast and KG-safe.

---

## Running the demo

```bash
# Start server (builds frontend first)
make dev

# Server runs at http://localhost:8000
# Navigate to /app → select a scenario → MissionControl screen

# From there:
# 1. Click any card in the "Live Data Feed" panel
# 2. Watch DaemonBar turn amber → green
# 3. Watch TelemetryFeed show the event cascade
# 4. Watch WorkerFleet workers respond
# 5. Trajectories auto-refresh in the background
```

---

## Known limitations

- Each `useAgentStream` consumer opens its own SSE connection to `/api/agent/stream`. With DaemonBar, OpsNavbar, and ScenarioSelect all mounted, there are up to 3 concurrent SSE connections. Functionally correct but not optimal — a future refactor should use a React context provider to share one connection.
- Demo push buttons don't reset to `idle` after a reload; state is in-memory only.
- The 4 demo events each append a record to the persona JSONL file permanently. Restarting the demo requires re-generating the data or reverting the file.
