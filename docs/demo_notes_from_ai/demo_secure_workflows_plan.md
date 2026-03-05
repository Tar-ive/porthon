# Demo Secure Workflows Implementation

## Scope
- Demo mode key family: `sk_demo_*`
- Primary workflows:
  - `demo.workflow.proactive.*`
  - `demo.workflow.figma_watch.*`
- Facebook watch stays available for legacy compatibility.

## Security Policy
- Reversible writes auto-run.
- Irreversible actions require explicit approval.
- Blocked actions emit `policy_blocked_action` events.

## Reactive Figma Flow
1. `demo.workflow.figma_watch.start` enables watch state.
2. `POST /v1/integrations/composio/webhook` ingests and normalizes events.
3. Runtime emits `integration.figma.webhook.received`.
4. `figma_worker.process_webhook_event` produces typed summary + draft reply.
5. Runtime stores pending items under `demo_artifacts.figma_watch.pending_items` with dedupe.

## Proactive Lean Caps
- Calendar: max 4 events.
- Notion leads: 1 pipeline + 3 seeded lead rows.
- Notion opportunity: 1 workspace + 1 progress page.
- Figma: optional milestone comment if file key provided.

## Observability
- `GET /v1/runtime` includes workflow artifacts in demo mode.
- `GET /v1/workers/map` includes task summaries and external links.
- `cycle_end.payload.cycle_duration_ms` remains exposed.

## Test Coverage
- `tests/fast/test_demo_workflows.py` contains exactly two tests:
  - proactive end-to-end
  - figma watch webhook end-to-end
- Both run offline while asserting mocked LLM boundary calls.
