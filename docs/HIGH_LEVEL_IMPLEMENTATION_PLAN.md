# High-Level Implementation Plan

## Objective
Build an always-on, scenario-driven companion agent for Theo using a Master-Worker architecture that continuously executes scenario-aligned actions across calendar, knowledge graph context, notion tracking, content, and figma planning.

## Product Principles
- One active scenario at a time.
- Hybrid loop execution: event-triggered + 15-minute tick.
- Preserve existing Composio auth and connected account IDs.
- Degrade-and-continue under failures (circuit breaker).
- Tiered write autonomy: low-risk auto, high-impact approval.
- Keep frontend changes minimal while exposing agent state clearly.

## Core Runtime Design
- AlwaysOnMaster owns scenario state, queue, budget policy, worker dispatch, health tracking, and checkpointing.
- Worker agents are specialized executors with skill-scoped responsibilities.
- Runtime state is persisted and queryable via APIs for frontend observability.
- Proactive outputs in V1: in-app and calendar updates.

## V1 Skill Set
- KG Search Skill
- Calendar Scheduler Skill
- Notion Leads Tracker Skill
- Notion Opportunity Tracker Skill
- Facebook Publisher Skill
- Figma Plan Generator Skill

## Safety + Control
- Approval required for high-impact writes (social publish, major schedule changes).
- Worker-level circuit breaker isolates failing integrations.
- Queue continues processing unaffected workers.

## API Additions
- `POST /api/agent/activate`
- `POST /api/agent/events`
- `GET /api/agent/state`
- `GET /api/agent/map`
- `GET /api/agent/stream`
- `POST /api/agent/approve`

## Testing Strategy
- Pytest-only execution model.
- Default fast deterministic suite for CI/local.
- Explicit live integration suite for Composio validation.
- `make test` as primary command.

## Delivery Approach
Deliver in 3 tested slices with frontend agent map visibility after each slice.
