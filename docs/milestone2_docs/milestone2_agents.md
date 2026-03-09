# Milestone 2: Always-On Deep Agents (Master-Worker Runtime)

## 1. Mission
Questline is now an always-on companion runtime, not a one-shot orchestrator. Theo chooses a scenario, and the system continuously executes scenario-aligned actions in the background with explicit worker responsibilities, health tracking, approvals, and realtime observability.

## 2. Runtime Loop

### Loop Pattern
- Hybrid trigger model:
  - Event-triggered cycles (scenario activation, user events, tool events)
  - Scheduled tick cycles (15-minute baseline)

### Cycle Phases
1. Load current runtime state.
2. Ingest events and scenario context.
3. Re-prioritize worker queue by scenario/horizon.
4. Dispatch concurrent workers with budgets.
5. Apply approvals/circuit-breaker policy.
6. Persist checkpoint and emit map/stream updates.

## 3. Scenario Policy
- Exactly one active scenario at a time.
- Scenario switch archives prior active scenario.
- New scenario reseeds queue across core workers.

## 4. Master-Worker Topology

### Master
- Queue ownership
- Budget enforcement
- Worker health and circuit states
- Approval queue
- State persistence
- Event stream publishing

### Workers
- `kg_worker`
- `calendar_worker`
- `notion_leads_worker`
- `notion_opportunity_worker`
- `facebook_worker`
- `figma_worker`

Workers execute skill-scoped tasks only and return structured results to the master.

## 5. Skills (V1)
- KG Search
- Calendar Scheduler
- Notion Leads Tracker
- Notion Opportunity Tracker
- Facebook Publisher
- Figma Plan Generator

Tool schema rules:
- concise contracts
- enums for controlled parameters
- minimal required fields
- descriptive names without plugin/service suffixes

## 6. Safety Model

### Tiered Write Autonomy
- Auto: low-risk updates
- Approval required: high-impact actions (e.g. publish social post, major schedule changes)

### Failure Handling
- Degrade-and-continue policy
- Worker-level circuit breaker opens after repeated failure
- Other workers continue while failed worker waits retry window

## 7. API Surface
- `POST /api/agent/activate`
- `POST /api/agent/events`
- `GET /api/agent/state`
- `GET /api/agent/map`
- `GET /api/agent/stream`
- `POST /api/agent/approve`

## 8. Frontend Integration (Minimal)
- Add an Agent Map panel inside chat view.
- After each backend slice, map reflects progressively richer runtime:
  - Slice 1: topology + static statuses
  - Slice 2: active scenario + queue + worker health
  - Slice 3: realtime cycle events + pending approvals

## 9. Testing Contract
- Pytest only.
- Fast deterministic suite is default (`make test`).
- Live composio suite is opt-in (`make test-live`).
- Each slice has a mandatory test gate before proceeding.

## 10. Result
This milestone establishes a durable shell for Theo's "game of life" companion: scenario-driven, always active, stateful, explainable, and ready for incremental worker/skill depth without architectural churn.
