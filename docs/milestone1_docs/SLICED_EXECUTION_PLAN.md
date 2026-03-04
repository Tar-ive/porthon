# Sliced Execution Plan (3 Slices)

## Slice 1: Foundation Shell + Read-Only Agent Map

### Backend
- Add deep-agent skeleton modules.
- Add runtime state models and JSON-backed state store.
- Add read-only APIs:
  - `GET /api/agent/state`
  - `GET /api/agent/map`
- Keep existing behavior for current quest/chat/scenario endpoints unchanged.

### Frontend (minimal)
- Add Agent Map panel to chat screen.
- Render topology + statuses from `/api/agent/map`.

### Test Gate (Pytest)
- State model validation tests.
- API contract tests for `/api/agent/state` and `/api/agent/map`.
- Frontend build check.

## Slice 2: Always-On Loop + Scenario Activation + Queue Dispatch

### Backend
- Implement always-on master loop with 15-minute tick and event-triggered cycles.
- Add APIs:
  - `POST /api/agent/activate`
  - `POST /api/agent/events`
- Implement concurrent dispatch and worker budgets.
- Add circuit-breaker degrade-and-continue behavior.

### Frontend (minimal)
- Trigger `/api/agent/activate` on scenario selection.
- Agent Map shows active scenario, queue depth, worker health.

### Test Gate (Pytest)
- Scenario switching and queue reseeding.
- Event-triggered cycle execution.
- Budget/circuit-breaker behavior.

## Slice 3: Skills + Tiered Approval + Realtime Stream

### Backend
- Add skill contract directories and SKILL.md files.
- Add tiered approval path and API:
  - `POST /api/agent/approve`
- Add realtime streaming API:
  - `GET /api/agent/stream`
- Split tests into `fast` and `live` suites.

### Frontend (minimal)
- Subscribe to `/api/agent/stream`.
- Show worker event timeline and pending approvals in agent map panel.

### Test Gate (Pytest)
- Approval gating and flow.
- Stream event emission.
- Fast suite by default; live suite opt-in.

## Delivery Policy
- Do not progress to next slice until current slice test gate passes.
- Keep all tests runnable via pytest and `make test`.
