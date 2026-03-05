# Questline API Reference

Base URL: `http://localhost:8000/v1`

## Conventions

### Prefixed Resource IDs

Every resource ID carries a type prefix so you can identify the resource without an API call:

| Prefix | Resource |
|--------|----------|
| `scen_` | Scenario |
| `qst_` | Quest |
| `act_` | Action |
| `apprv_` | Approval |
| `evt_` | Event |
| `wrkr_` | Worker |
| `msg_` | Message |
| `task_` | Task |

IDs use ULID encoding after the prefix (e.g. `scen_01j5a3bkwq...`).

### Idempotency

All mutating requests (`POST`, `PUT`, `DELETE`) accept an `Idempotency-Key` header. If you resend a request with the same key within 24 hours, you receive the original response with an `idempotent-replayed: true` header. The key is scoped to `method + path + idempotency-key`.

### Pagination

All list endpoints use cursor-based pagination:

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int (1-100, default 20) | Page size |
| `starting_after` | string | ID of the last item from the previous page |

Responses include `has_more: true` when additional pages exist.

### Expansion

Use `expand[]` query parameters to inline related objects instead of returning bare IDs:

```
GET /v1/scenarios/scen_xxx?expand[]=patterns
GET /v1/workers?expand[]=skills
GET /v1/quests/qst_xxx?expand[]=tasks.worker&expand[]=scenario
```

Dot-notation supports up to 3 levels of nesting.

### Structured Errors

All errors return:

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "resource_missing",
    "message": "The requested scenario does not exist.",
    "param": "scenario_id",
    "doc_url": "https://api.porthon.ai/docs/errors#resource_missing"
  }
}
```

### Authentication

Pass a bearer token via `Authorization: Bearer sk_demo_default` (test mode) or `Authorization: Bearer sk_live_...` (live mode). The `livemode` field on every resource reflects the key type.

### API Version

Pin your version with `X-Api-Version: 2026-03-01`.

### Metadata

Every resource carries a `metadata` key-value store (`dict[str, str]`) for custom state.

---

## Endpoints

### Health

#### GET /v1/health

Returns server status.

**Parameters:** None

**curl:**
```bash
curl http://localhost:8000/v1/health \
  -H "Authorization: Bearer sk_demo_default"
```

**Response:**
```json
{
  "object": "health",
  "status": "ok",
  "backend": "openai",
  "rag": false,
  "livemode": false
}
```

---

### Scenarios

#### GET /v1/scenarios

List generated scenarios for a persona.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `persona_id` | string | `p05` | Persona to generate scenarios for |
| `limit` | int | 20 | Page size |
| `starting_after` | string | — | Cursor |
| `expand[]` | string | — | Expansion paths |

**curl:**
```bash
curl "http://localhost:8000/v1/scenarios?persona_id=p05" \
  -H "Authorization: Bearer sk_demo_default"
```

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "scen_01j5...",
      "object": "scenario",
      "created": 1741100000,
      "livemode": false,
      "metadata": {},
      "title": "Freelance Breakthrough",
      "horizon": "1yr",
      "likelihood": "most_likely",
      "summary": "Theo lands 3 recurring clients...",
      "tags": ["career", "finance"],
      "patterns": ["pat_01", "pat_02"]
    }
  ],
  "has_more": false,
  "url": "/v1/scenarios"
}
```

#### GET /v1/scenarios/{scenario_id}

Retrieve a single scenario.

| Parameter | Type | Description |
|-----------|------|-------------|
| `scenario_id` | string | Path param — prefixed ID |
| `expand[]` | string | e.g. `patterns` |

**curl:**
```bash
curl "http://localhost:8000/v1/scenarios/scen_01j5...?expand[]=patterns" \
  -H "Authorization: Bearer sk_demo_default"
```

**Response:** Same shape as a single item in the list `data` array.

**Errors:** `404` with `resource_missing` if scenario not found.

---

### Quests

#### POST /v1/quests

Activate a quest from a scenario. Runs the full pipeline: scenario lookup, action planning, master loop activation.

| Body Field | Type | Required | Description |
|------------|------|----------|-------------|
| `scenario_id` | string | yes | ID of the scenario to activate |
| `persona_id` | string | no (default `p05`) | Persona ID |

**curl:**
```bash
curl -X POST http://localhost:8000/v1/quests \
  -H "Authorization: Bearer sk_demo_default" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: idem_activate_001" \
  -d '{"scenario_id": "scen_01j5...", "persona_id": "p05"}'
```

**Response:**
```json
{
  "id": "qst_01j5...",
  "object": "quest",
  "created": 1741100000,
  "livemode": false,
  "metadata": {},
  "scenario": "scen_01j5...",
  "persona_id": "p05",
  "status": "active",
  "seeded_tasks": 3,
  "cycle": {},
  "tasks": ["task_01", "task_02"]
}
```

**Errors:** `504` timeout, `500` internal error.

#### GET /v1/quests

List active quests (currently at most one).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | — | Filter by status |
| `limit` | int | 20 | Page size |
| `starting_after` | string | — | Cursor |
| `expand[]` | string | — | e.g. `tasks.worker`, `scenario` |

**curl:**
```bash
curl "http://localhost:8000/v1/quests?expand[]=tasks.worker&expand[]=scenario" \
  -H "Authorization: Bearer sk_demo_default"
```

#### GET /v1/quests/{quest_id}

Retrieve a single quest.

**Errors:** `404` with `resource_missing` (persistent quest store not yet implemented).

---

### Actions

#### POST /v1/actions

Generate actions for a scenario.

| Body Field | Type | Required | Description |
|------------|------|----------|-------------|
| `scenario_id` | string | yes | Scenario to plan actions for |

**curl:**
```bash
curl -X POST http://localhost:8000/v1/actions \
  -H "Authorization: Bearer sk_demo_default" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: idem_actions_001" \
  -d '{"scenario_id": "scen_01j5..."}'
```

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "act_01j5...",
      "object": "action",
      "created": 1741100000,
      "livemode": false,
      "metadata": {},
      "scenario": "scen_01j5...",
      "title": "Block 2 hours for portfolio review",
      "description": "Block 2 hours for portfolio review",
      "data_ref": "calendar:2026-03-05T10:00",
      "pattern_id": "pat_01",
      "rationale": "Consistent morning focus blocks correlate with...",
      "compound_summary": ""
    }
  ],
  "has_more": false,
  "url": "/v1/actions"
}
```

**Errors:** `404` scenario not found, `504` timeout, `500` internal error.

---

### Approvals

#### GET /v1/approvals

List pending and resolved approvals.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 20 | Page size |
| `starting_after` | string | — | Cursor |

**curl:**
```bash
curl http://localhost:8000/v1/approvals \
  -H "Authorization: Bearer sk_demo_default"
```

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "apprv_01j5...",
      "object": "approval",
      "created": 1741100000,
      "livemode": false,
      "metadata": {},
      "task_id": "task_01",
      "worker_id": "calendar",
      "reason": "Creating a calendar event requires approval",
      "payload": {"event_title": "Focus block"},
      "decision": null,
      "resolved_at": null
    }
  ],
  "has_more": false,
  "url": "/v1/approvals"
}
```

#### GET /v1/approvals/{approval_id}

Retrieve a single approval.

#### POST /v1/approvals/{approval_id}/resolve

Approve or reject a pending approval.

| Body Field | Type | Required | Description |
|------------|------|----------|-------------|
| `decision` | string | yes | `"approved"` or `"rejected"` |

**curl:**
```bash
curl -X POST http://localhost:8000/v1/approvals/apprv_01j5.../resolve \
  -H "Authorization: Bearer sk_demo_default" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: idem_approve_001" \
  -d '{"decision": "approved"}'
```

**Response:**
```json
{
  "id": "apprv_01j5...",
  "object": "approval",
  "decision": "approved",
  "cycle": {}
}
```

**Errors:** `404` approval not found, `400` invalid request.

---

### Events

#### POST /v1/events

Ingest a custom event into the master loop.

| Body Field | Type | Required | Description |
|------------|------|----------|-------------|
| `type` | string | yes | Event type (e.g. `"calendar_update"`) |
| `payload` | object | no | Arbitrary data |

**curl:**
```bash
curl -X POST http://localhost:8000/v1/events \
  -H "Authorization: Bearer sk_demo_default" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: idem_event_001" \
  -d '{"type": "calendar_update", "payload": {"item": "meeting"}}'
```

**Response:**
```json
{
  "id": "evt_01j5...",
  "object": "event",
  "created": 1741100000,
  "livemode": true,
  "metadata": {},
  "type": "calendar_update",
  "payload": {"item": "meeting"},
  "cycle": {}
}
```

#### GET /v1/events

List recent events.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `quest` | string | — | Filter by quest ID |
| `limit` | int | 20 | Page size |
| `starting_after` | string | — | Cursor |

**curl:**
```bash
curl "http://localhost:8000/v1/events?quest=qst_01j5...&limit=20" \
  -H "Authorization: Bearer sk_demo_default"
```

#### GET /v1/events/stream

Server-Sent Events stream of real-time events. Sends `data: {...}\n\n` frames. Keepalive comments every 20 seconds.

**curl:**
```bash
curl -N http://localhost:8000/v1/events/stream \
  -H "Authorization: Bearer sk_demo_default"
```

---

### Workers

#### GET /v1/workers

List all registered workers.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 20 | Page size |
| `starting_after` | string | — | Cursor |
| `expand[]` | string | — | `skills` to inline skill definitions |

**curl:**
```bash
curl "http://localhost:8000/v1/workers?expand[]=skills" \
  -H "Authorization: Bearer sk_demo_default"
```

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "wrkr_calendar",
      "object": "worker",
      "created": 1741100000,
      "livemode": false,
      "metadata": {},
      "label": "CalendarWorker",
      "status": "ready",
      "queue_depth": 0,
      "last_error": null,
      "skills": []
    }
  ],
  "has_more": false,
  "url": "/v1/workers"
}
```

#### GET /v1/workers/map

Returns the full worker map (topology, capabilities, status).

**curl:**
```bash
curl http://localhost:8000/v1/workers/map \
  -H "Authorization: Bearer sk_demo_default"
```

#### GET /v1/workers/skills

List all registered skills across all workers.

#### GET /v1/workers/{worker_id}

Retrieve a single worker. Supports `expand[]=skills`.

---

### Notion Leads CRM

#### POST /v1/notion/leads/setup

Create or reuse Theo's deterministic Notion Leads workspace and enforce schema.

| Body Field | Type | Required | Description |
|------------|------|----------|-------------|
| `parent_page_id` | string | no | Root page to host the `Leads` database |
| `database_title` | string | no | Default `Leads` |
| `data_source_title` | string | no | Default `Theo Leads` |
| `database_id` | string | no | Force existing DB reuse |
| `data_source_id` | string | no | Force existing data source reuse |

#### POST /v1/notion/leads/sync

Deterministic snapshot sync: create/update rows and archive stale rows.

| Body Field | Type | Required | Description |
|------------|------|----------|-------------|
| `leads` | array | yes | Lead payload list |
| `strict_reconcile` | boolean | no | Default `true`; archives rows not in snapshot |

#### GET /v1/notion/leads

List current leads with optional CRM view filters.

| Query Field | Type | Description |
|-------------|------|-------------|
| `view` | string | `today_followups`, `high_value_focus`, `warm_inbound`, `prospecting` |
| `status` | string | Filter by lead status |
| `source` | string | Filter by source |
| `lead_type` | string | Filter by lead type |
| `min_deal_size` | number | Used by `high_value_focus` |
| `q` | string | Case-insensitive search |

#### PATCH /v1/notion/leads/{lead_key}

Patch one lead by deterministic key (`name::source`).

#### POST /v1/notion/leads/realtime

Queue a real-time notion leads task through the runtime loop.

| Body Field | Type | Required | Description |
|------------|------|----------|-------------|
| `action` | string | yes | `sync_leads`, `upsert_lead`, `patch_lead` |
| `task_payload` | object | no | Worker payload |
| `priority` | int | no | Queue priority (lower runs first) |

#### GET /v1/notion/leads/os/state

Return current Lead OS runtime view: pod statuses, recommended actions, and sustainability snapshot.

#### POST /v1/notion/leads/os/tick

Run one deterministic Lead OS scheduling cycle over current leads.

| Body Field | Type | Required | Description |
|------------|------|----------|-------------|
| `top_n` | int | no | Max recommendations to keep (default 12) |

#### POST /v1/notion/leads/os/dispatch

Enqueue top Lead OS actions into runtime queue (`notion_leads_worker`).

| Body Field | Type | Required | Description |
|------------|------|----------|-------------|
| `limit` | int | no | Max actions to dispatch |
| `min_score` | number | no | Minimum recommendation score |
| `priority` | int | no | Queue priority |
| `dry_run` | bool | no | If true, do not enqueue |

#### POST /v1/figma/comments/{comment_id}/promote-to-lead

Promote a pending Figma collaboration comment into a deterministic Notion lead and persist comment/actor linkage.

#### POST /v1/figma/comments/poll

Poll Figma comments directly (`GET /v1/files/{file_key}/comments`) and ingest them into the same pending-comment flow used by webhooks.

---

### Messages

#### POST /v1/messages

Chat with the AI agent. Returns a Server-Sent Events stream.

| Body Field | Type | Required | Description |
|------------|------|----------|-------------|
| `messages` | array | yes | Chat messages `[{role, content}]` |
| `scenario` | object | no | `{id, title, horizon, likelihood, summary}` for context |

**curl:**
```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Authorization: Bearer sk_demo_default" \
  -H "Content-Type: application/json" \
  -N \
  -d '{
    "messages": [{"role": "user", "content": [{"type": "text", "text": "What should I focus on today?"}]}],
    "scenario": {"id": "scen_01j5...", "title": "Freelance Breakthrough", "horizon": "1yr", "likelihood": "most_likely", "summary": "..."}
  }'
```

**Response:** SSE stream (`text/event-stream`). Response includes `x-porthon-intent` header with classified intent (e.g. `casual`, `planning`, `reflection`).

---

### Runtime

#### GET /v1/runtime

Returns the full agent runtime state: active scenario, worker statuses, queue, event history.

**curl:**
```bash
curl http://localhost:8000/v1/runtime \
  -H "Authorization: Bearer sk_demo_default"
```

**Response:**
```json
{
  "object": "runtime",
  "active_scenario": null,
  "workers": [],
  "queue": [],
  "approvals": [],
  "event_history": []
}
```

---

## Error Codes

| HTTP | Code | Type | When |
|------|------|------|------|
| 400 | `invalid_request` | `invalid_request_error` | Malformed body or invalid parameter |
| 404 | `resource_missing` | `invalid_request_error` | Resource ID not found |
| 500 | `internal_error` | `api_error` | Unhandled server error |
| 504 | `timeout` | `invalid_request_error` | Agent pipeline exceeded 30s timeout |
