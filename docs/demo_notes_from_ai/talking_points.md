# Demo Talking Points

Key points to highlight during the Questline API demo.

## 1. Deep Expansion (expand[])

"Our API follows Stripe conventions. Instead of making 5 requests to assemble a quest with its tasks, workers, and scenario, you pass `expand[]=tasks.worker&expand[]=scenario` and get everything in one call. This is designed for agent consumption -- an LLM agent making API calls should minimize round-trips."

- Show: `GET /v1/quests?expand[]=tasks.worker&expand[]=scenario`
- Without expand: nested objects are bare ID strings
- With expand: full objects inlined, up to 3 levels deep

## 2. Idempotency

"Every mutating endpoint accepts an `Idempotency-Key` header. If an agent retries a timed-out quest activation, the server returns the cached response instead of creating a duplicate quest. The cache lasts 24 hours and is scoped to method + path + key."

- Show: POST /v1/quests twice with the same key
- Second response has `idempotent-replayed: true` header
- Critical for reliability in agent-driven workflows where retries are common

## 3. Approval Flow

"Actions are tiered by risk. Read-only operations auto-execute. Side-effect operations -- creating calendar events, posting to social media, updating a CRM -- pause for human approval. The agent proposes, the human disposes."

- Show: `GET /v1/approvals` to see pending items
- Show: `POST /v1/approvals/{id}/resolve` with `{"decision": "approved"}`
- Rejected approvals are logged but the action is skipped
- This is the safety layer between AI recommendations and real-world actions

## 4. Test Mode

"We are running in test mode using `sk_demo_default`. The entire API surface works identically, but no external services are called. Switch to a `sk_live_` key and the same quest activation would create real calendar events and Notion entries through Composio."

- Every response includes `livemode: false`
- Same code path, same approval flow, stubbed external actions
- Any `sk_demo_*` key activates test mode

## 5. Structured Errors

"Errors are machine-readable. Every error response has a `type`, `code`, `message`, optional `param`, and a `doc_url`. An agent can parse the `code` field to decide whether to retry (`timeout`), fix the request (`invalid_request`), or give up (`resource_missing`)."

- Show a 404 by requesting a non-existent scenario ID
- Response structure:
  ```json
  {
    "error": {
      "type": "invalid_request_error",
      "code": "resource_missing",
      "message": "Scenario not found.",
      "param": "scenario_id",
      "doc_url": "https://api.porthon.ai/docs/errors#resource_missing"
    }
  }
  ```

## 6. Prefixed IDs

"Every resource ID carries its type as a prefix: `scen_` for scenarios, `qst_` for quests, `apprv_` for approvals. An agent can look at any ID and immediately know what kind of resource it is, without an API call. This is a Stripe pattern that makes agent tooling much simpler."

- 8 prefixes: `scen_`, `qst_`, `act_`, `apprv_`, `evt_`, `wrkr_`, `msg_`, `task_`
- IDs use ULID encoding for sortability and uniqueness

## 7. Real-Time Event Stream

"The `/v1/events/stream` endpoint provides Server-Sent Events. An agent or UI can subscribe and receive every state change in real time -- task dispatches, worker completions, approval requests. No polling required."

- Show: `GET /v1/events/stream` (curl with `-N` flag)
- Keepalive comments every 20 seconds
- Each event carries an `evt_` prefixed ID

## 8. Agent-First Design

"This API is built for LLM agents, not just humans. The decision tree is simple: list scenarios, pick one, activate a quest, resolve approvals, monitor events. Every response is structured JSON with consistent shapes. The expand system eliminates follow-up requests. The idempotency system makes retries safe. An agent can use this API as a tool without any special SDK."

## Narrative Arc for the Demo

1. **Health check** -- "The system is up, we are in test mode"
2. **Scenarios** -- "Here are 3 life projections generated from Theo's data"
3. **Expansion** -- "We can drill into patterns without extra requests"
4. **Quest activation** -- "One call to activate the full agent pipeline"
5. **Worker map** -- "Here are the agents that will execute the quest"
6. **Approvals** -- "Some actions need human sign-off"
7. **Events** -- "We can see everything that happened"
8. **Chat** -- "The agent is context-aware and can discuss the quest"
9. **Idempotency** -- "Safe to retry -- same key, same result, no duplicates"
