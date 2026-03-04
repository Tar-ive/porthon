# Deep Agent API Design Specification

This document redesigns the Deep Agent API to follow robust, "agent-consumable" best practices. By adopting these principles (inspired by Stripe), the API becomes highly predictable, safe for autonomous agents to consume, and extremely resilient for frontend integration.

## 1. Resource Identity & Consistent Base Schema

Every object returned by the API follows a consistent base schema, allowing generic reasoning over any resource.

### Base Schema Elements
Every resource guarantees the presence of these fields:
* [id](file:///Users/tarive/porthon/src/backend/agents/composio_tools.py#96-100): A prefixed string identifier (e.g., `scen_1A2b...`). The prefix strictly encodes the entity type.
* `object`: A string explicitly declaring the type (e.g., `"scenario"`).
* `created`: A Unix timestamp of creation.
* `livemode`: Boolean indicating if this is test data (`false`) or real production data (`true`).

### Registered Prefixes
| Prefix | Object Type | Example |
|---|---|---|
| `scen_` | [scenario](file:///Users/tarive/porthon/src/backend/main.py#112-123) | `scen_01JDF2...` (Quest Scenario) |
| `qst_` | [quest](file:///Users/tarive/porthon/src/backend/main.py#96-101) | `qst_8A9b...` (Active Quest Instance) |
| `apprv_` | [approval](file:///Users/tarive/porthon/src/backend/app/api/routes_agent.py#73-76) | `apprv_4Fd3...` (Pending Human Approval) |
| `evt_` | [event](file:///Users/tarive/porthon/src/backend/deepagent/loop.py#157-178) | `evt_k92L...` (Worker Execution Event) |
| `msg_` | `message` | `msg_P2m1...` (Chat Message) |
| `wrkr_` | [worker](file:///Users/tarive/porthon/src/backend/deepagent/workers/__init__.py#11-21) | `wrkr_c3xZ...` (Deep Agent Worker definition) |

*Heuristic Check:* If an endpoint expects an approval but receives `scen_1A2b`, the client/agent should instantly reject it based on the prefix mismatch without making an API call.

---

## 2. Safety, Idempotency, and Mutations

All state-changing operations (`POST`, `PUT`, `DELETE`) require an `Idempotency-Key` header. This guarantees that network retries never result in duplicated actions (like double-billing or double-posting to Facebook).

### Example: Activating a Scenario

```http
POST /v1/quests
Idempotency-Key: req_01H8...
X-Api-Version: 2026-03-01
Content-Type: application/json

{
  "scenario_id": "scen_freelance_2026",
  "metadata": {
    "client_session": "sess_web_88291",
    "experiment_cohort": "b"
  }
}
```

*Heuristic:* The frontend must generate a UUID for the `Idempotency-Key` and reuse it if the request times out or drops. The API guarantees the exact same `qst_xxx` object is returned within a 24h window without triggering two backend quests.

---

## 3. Data Fetching & Expandable Objects

To avoid N+1 requests over the network while keeping payloads minimal, related resources are returned as IDs by default, but can be expanded via the `expand[]` query parameter.

### Example: Fetching the active quest

```json
// GET /v1/quests/qst_8A9b
{
  "id": "qst_8A9b",
  "object": "quest",
  "scenario": "scen_freelance", // Unexpanded ID
  "livemode": true,
  "created": 1741103211,
  "status": "active"
}
```

### With Expansion

```json
// GET /v1/quests/qst_8A9b?expand[]=scenario
{
  "id": "qst_8A9b",
  "object": "quest",
  "scenario": {
    "id": "scen_freelance",
    "object": "scenario",
    "title": "Full-Time Freelance",
    "livemode": true,
    "created": 1740900000
  },
  "livemode": true,
  "created": 1741103211,
  "status": "active"
}
```

*Heuristic:* The frontend requests expansions only for the views currently rendered on screen (e.g., expanding the [scenario](file:///Users/tarive/porthon/src/backend/main.py#112-123) to render the Map Panel).

---

## 4. Cursor-Based Pagination

Offset pagination (`page=2`) is strictly forbidden due to data drift during active agent iterations. All list endpoints use cursor-based pagination.

```http
GET /v1/events?quest=qst_8A9b&limit=10&starting_after=evt_k92L
```

### Standard List Object Response
```json
{
  "object": "list",
  "data": [
    { "id": "evt_next1", "object": "event", ... },
    { "id": "evt_next2", "object": "event", ... }
  ],
  "has_more": true,
  "url": "/v1/events"
}
```

*Heuristic:* Treat `has_more` as the ultimate source of truth. If `true`, pass the ID of the last item in [data](file:///Users/tarive/porthon/data) to `starting_after` for the next chunk.

---

## 5. Error Model for Agents and UI

Errors are structured to be parsed programmatically by agents, and safely displayed by user interfaces.

### Standard Error Object
```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "resource_missing",
    "message": "The requested scenario 'scen_nonexistent' does not exist.",
    "param": "scenario_id",
    "doc_url": "https://api.porthon.ai/docs/errors#resource_missing"
  }
}
```

### Recommended Error Types
* `api_error`: Internal server errors (Master Loop crashed).
* `invalid_request_error`: Validation failures, missing parameters.
* `idempotency_error`: An idempotency key was reused with a different payload.
* `state_conflict_error`: e.g., Trying to approve an `apprv_xxx` that is already resolved.

*Heuristic for Frontend:* Use `param` to highlight the exact input field in red. Show the `message` to the user.
*Heuristic for Agents:* Parse the `code` to run an AST-style self-correction (e.g., if `code == "missing_metadata"`, the agent rewrites the payload and tries again).

---

## 6. Extensibility Hooks (Metadata)

Core resources (`quests`, [scenarios](file:///Users/tarive/porthon/src/backend/main.py#112-123), `approvals`, `users`) support an updatable `metadata` key-value store. 

```json
"metadata": {
  "framer_canvas_id": "frm_xs912L",
  "frontend_theme": "dark"
}
```
*Heuristic:* Never block a feature because the API schema lacks a specific field. Store UI-centric state, routing parameters, or external system mappings in `metadata`. The backend guarantees it will blindly persist and return these keys.

---

## 7. Versioning and Environment Separation

* **Test vs Live Environments:** Every API key dictates the environment. The Master Loop checks the key prefix (`sk_test_...` vs `sk_live_...`). If a test key is used, `livemode: false` is forced on all created resources. The agent will run dry-runs on Composio integrations.
* **API Versioning:** The frontend pins its expected shape via an HTTP header: `X-Api-Version: 2026-03-01`. The backend maintains transformation layers so breaking changes in the Master Loop don't break old UI clients.

---

## 8. Contrast: Stripe-Like Spec vs. Current Backend API

Currently, [app/api/routes_agent.py](file:///Users/tarive/porthon/src/backend/app/api/routes_agent.py) and [main.py](file:///Users/tarive/porthon/src/backend/main.py) represent a functional but "V0" shape. Here is the contrast highlighting why the new design is necessary for a robust frontend/agent ecosystem:

| Feature | Current API ([routes_agent.py](file:///Users/tarive/porthon/src/backend/app/api/routes_agent.py)) | New Stripe-Like Design | Why the Change Matters for Deep Agents |
|---|---|---|---|
| **Resource Identity** | Random IDs (`"freelance-full-time"`) without type markers. | Prefixed IDs (`scen_...`, `qst_...`) globally. | An agent can immediately infer what an object is just by looking at the string ID (circuit breaking bad inputs). |
| **Response Schema** | Flat dictionaries with varied shapes ([ActivateAgentRequest](file:///Users/tarive/porthon/src/backend/app/api/routes_agent.py#25-32)). | Consistent base ([id](file:///Users/tarive/porthon/src/backend/agents/composio_tools.py#96-100), `object`, `created`, `livemode`). | Generic components can render *any* resource. The frontend doesn't need custom parsers for every new endpoint. |
| **Safety / Retries** | No idempotency. Retrying `POST /api/agent/activate` creates multiple loops. | `Idempotency-Key` headers required on all mutating POSTs. | If the connection drops, agents can safely retry without duplicating events in the real world (e.g., booking two calendar events). |
| **Pagination** | (Not currently implemented for streams/state) | Cursor-based with `starting_after` and `has_more`. | State tables grow indefinitely. Offset pagination skips items during active writes. Cursors guarantee accurate lists. |
| **Fetching Depth** | Fixed shapes. `GET /state` returns the entire Master Loop dump. | Granular IDs with `expand[]` query logic. | Prevents sending a 5MB JSON blob to mobile clients by letting them request only the nested data they need. |
| **Error Handling** | Unhandled 500s or simple string messages. | Structured `{type, code, param, message}` object. | The frontend can programmatically map `param` to a UI field to show a red error state instead of a generic toast notification. |
| **Custom State** | Not supported. | `metadata` KV store on all resources. | The UI can save custom route states or rendering flags without backend engineers altering the Pydantic schemas. |
