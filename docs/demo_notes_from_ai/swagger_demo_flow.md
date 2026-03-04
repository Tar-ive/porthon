# Swagger UI Demo Walkthrough -- Theo Nakamura (p05)

This is a step-by-step guide for demonstrating the Questline API through the Swagger UI. Each step builds on the previous one to show the full quest lifecycle.

## Prerequisites

- Server running: `cd src/backend && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000`
- OpenAI API key set in `.env` (or will fall back to deterministic scenarios)

---

## Step 1: Open Swagger UI

Navigate to [http://localhost:8000/docs](http://localhost:8000/docs) in your browser.

## Step 2: Authorize

Click the **Authorize** button (lock icon, top right). Enter:

```
Bearer sk_test_demo
```

This puts all requests in test mode (`livemode: false`). No real external actions will fire.

## Step 3: GET /v1/health

Expand `GET /v1/health`, click **Try it out**, then **Execute**.

Expected response:
```json
{
  "object": "health",
  "status": "ok",
  "backend": "openai",
  "rag": false,
  "livemode": false
}
```

Talking point: "The API tells us the backend provider and whether the knowledge graph is active. Notice `livemode: false` because we used a test key."

## Step 4: GET /v1/scenarios?persona_id=p05

Expand `GET /v1/scenarios`. Set `persona_id` to `p05`. Execute.

You will receive a list of 3 scenarios (1yr/5yr/10yr) generated from Theo's behavioral data. Copy one `id` value (e.g. `scen_01j5...`) for the next steps.

Talking point: "These scenarios are generated in real-time from Theo's financial, calendar, and social data. Each one references the behavioral patterns that informed it."

## Step 5: GET /v1/scenarios/{scenario_id}?expand[]=patterns

Expand `GET /v1/scenarios/{scenario_id}`. Paste the `scen_` ID. Add `patterns` to the `expand[]` parameter. Execute.

Talking point: "With `expand[]=patterns`, we inline the full pattern objects instead of just IDs. This eliminates the need for follow-up requests -- a Stripe-style convention designed for agent consumption."

## Step 6: POST /v1/quests (with Idempotency-Key)

Expand `POST /v1/quests`. Set the request body:

```json
{
  "scenario_id": "scen_01j5...",
  "persona_id": "p05"
}
```

Add the header `Idempotency-Key: demo_quest_001` (in Swagger, add it via the header parameter or use curl separately).

Execute. The response shows the activated quest with `qst_` ID, seeded tasks, and cycle state.

Talking point: "This single call runs the full pipeline: finds the scenario, generates actions, seeds tasks into the worker queue, and starts the master loop. The Idempotency-Key ensures this is safe to retry."

## Step 7: GET /v1/quests?expand[]=tasks.worker&expand[]=scenario

Expand `GET /v1/quests`. Add both expansion params. Execute.

Talking point: "Deep expansion -- `tasks.worker` resolves two levels deep. We get the quest, its tasks, and the worker assigned to each task, all in one response."

## Step 8: GET /v1/workers/map

Expand `GET /v1/workers/map`. Execute.

This returns the full worker topology: which workers exist, their capabilities, and current status.

Talking point: "This is the agent map -- KgWorker for knowledge graph memory, CalendarWorker for scheduling, NotionLeadsWorker for CRM, FigmaWorker for design, FacebookWorker for social drafting. Each worker has a defined set of skills and approval tiers."

## Step 9: GET /v1/approvals

Expand `GET /v1/approvals`. Execute.

If the quest seeded any tasks that require human approval (e.g. creating a calendar event, posting to social media), they appear here with `decision: null`.

Talking point: "The approval flow is tiered. Read-only actions auto-execute. Actions with side effects pause here for human review. This is the safety layer."

## Step 10: POST /v1/approvals/{approval_id}/resolve

If approvals exist, copy an `apprv_` ID. Set the body:

```json
{
  "decision": "approved"
}
```

Add `Idempotency-Key: demo_approve_001`. Execute.

Talking point: "Once approved, the worker executes the action. Rejected approvals are logged but the action is skipped. The decision is permanent."

## Step 11: GET /v1/events?quest=qst_xxx&limit=20

Expand `GET /v1/events`. Set `quest` to the `qst_` ID from step 6. Set `limit` to `20`. Execute.

This shows the chronological event history for the quest: task dispatches, worker executions, approvals, completions.

Talking point: "Every state change in the system emits an event. Agents can poll this endpoint or subscribe to the SSE stream for real-time updates."

## Step 12: POST /v1/messages (chat with SSE)

Expand `POST /v1/messages`. Set the body:

```json
{
  "messages": [
    {
      "role": "user",
      "content": [{"type": "text", "text": "What should I focus on this week given my quest?"}]
    }
  ],
  "scenario": {
    "id": "scen_01j5...",
    "title": "Freelance Breakthrough",
    "horizon": "1yr",
    "likelihood": "most_likely",
    "summary": "Theo lands 3 recurring clients..."
  }
}
```

Execute. The response streams as SSE. In Swagger the streamed text appears in the response body.

Talking point: "The chat agent is context-aware. It knows the active scenario, uses the knowledge graph for retrieval, and classifies the user's intent to shape its response style."

## Step 13: Retry Step 6 with Same Idempotency-Key

Re-execute `POST /v1/quests` with the exact same body and `Idempotency-Key: demo_quest_001`.

The response is identical to step 6. Check the response headers for `idempotent-replayed: true`.

Talking point: "Same key, same response, no duplicate side effects. This is critical for agents that retry on timeouts. The idempotency cache lasts 24 hours and is scoped to method + path + key."
