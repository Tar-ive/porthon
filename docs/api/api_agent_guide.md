# Questline API -- Agent Consumption Guide

Use this document as a system prompt or reference when an LLM agent needs to interact with the Questline API.

## Decision Tree: Which Endpoint Do I Call?

```
START
  |
  +-- Need server status?
  |     -> GET /v1/health
  |
  +-- Need life scenarios for a persona?
  |     -> GET /v1/scenarios?persona_id=p05
  |     -> GET /v1/scenarios/{id} for a single scenario
  |
  +-- Want to activate a scenario as a quest?
  |     -> POST /v1/quests  {scenario_id, persona_id}
  |
  +-- Need concrete daily actions from a scenario?
  |     -> POST /v1/actions  {scenario_id}
  |
  +-- Need to check or resolve approval gates?
  |     -> GET /v1/approvals  (list pending)
  |     -> POST /v1/approvals/{id}/resolve  {decision: "approved"|"rejected"}
  |
  +-- Need to see what workers are available?
  |     -> GET /v1/workers  or  GET /v1/workers/map
  |     -> GET /v1/workers/skills  (all skills)
  |
  +-- Need to manage Theo's Notion leads CRM deterministically?
  |     -> POST /v1/notion/leads/setup
  |     -> POST /v1/notion/leads/sync
  |     -> GET /v1/notion/leads?view=today_followups
  |     -> PATCH /v1/notion/leads/{lead_key}
  |     -> POST /v1/notion/leads/realtime
  |
  +-- Need Lead OS pod scheduling state and dispatch?
  |     -> GET /v1/notion/leads/os/state
  |     -> POST /v1/notion/leads/os/tick
  |     -> POST /v1/notion/leads/os/dispatch
  |
  +-- Need to convert a Figma comment into a CRM lead?
  |     -> POST /v1/figma/comments/{comment_id}/promote-to-lead
  |
  +-- Can't use webhooks and need direct comment polling?
  |     -> POST /v1/figma/comments/poll
  |
  +-- Need to send an external event into the loop?
  |     -> POST /v1/events  {type, payload}
  |
  +-- Need event history or real-time stream?
  |     -> GET /v1/events?quest=qst_xxx&limit=20
  |     -> GET /v1/events/stream  (SSE)
  |
  +-- Want to chat with the persona agent?
  |     -> POST /v1/messages  {messages, scenario?}
  |
  +-- Need full runtime state dump?
        -> GET /v1/runtime
```

## ID Prefix Lookup Table

| Prefix | Resource | Example |
|--------|----------|---------|
| `scen_` | Scenario | `scen_01j5a3bkwq...` |
| `qst_` | Quest | `qst_01j5a3bkwq...` |
| `act_` | Action | `act_01j5a3bkwq...` |
| `apprv_` | Approval | `apprv_01j5a3bkwq...` |
| `evt_` | Event | `evt_01j5a3bkwq...` |
| `wrkr_` | Worker | `wrkr_calendar` |
| `msg_` | Message | `msg_01j5a3bkwq...` |
| `task_` | Task | `task_01j5a3bkwq...` |

Rule: You can always infer the resource type from the prefix. If you see `scen_`, it is a scenario. No need to call the API to determine the type.

## Retry and Idempotency Instructions

1. For every `POST`, `PUT`, or `DELETE` request, generate a unique `Idempotency-Key` header value.
2. Use a deterministic key derived from the operation intent (e.g. `activate_quest_{scenario_id}_{timestamp}`).
3. If a request times out or returns a 5xx, retry with the **same** `Idempotency-Key`.
4. The server caches responses for 24 hours keyed on `method + path + idempotency-key`.
5. A replayed response includes `idempotent-replayed: true` header -- the operation was NOT executed again.
6. For `GET` requests, no idempotency key is needed. Just retry.

### Recommended retry policy

- Max 3 retries
- Backoff: 1s, 2s, 4s
- Only retry on: network error, 429, 500, 502, 503, 504
- Never retry 400/404 (fix the request instead)

## expand[] Cheat Sheet

Use `expand[]` query params to inline related objects. Avoids N+1 requests.

| Endpoint | Supported Expansions |
|----------|---------------------|
| `GET /v1/scenarios/{id}` | `patterns` |
| `GET /v1/quests` | `tasks.worker`, `scenario` |
| `GET /v1/quests/{id}` | `tasks.worker`, `scenario` |
| `GET /v1/workers` | `skills` |
| `GET /v1/workers/{id}` | `skills` |

### Dot-notation rules

- Up to 3 levels: `tasks.worker.skills`
- Multiple expansions: `?expand[]=tasks.worker&expand[]=scenario`
- Without expansion, nested objects return as bare ID strings
- With expansion, the ID string is replaced by the full object

## Error Recovery Strategies

### `resource_missing` (404)

The resource ID does not exist. Common causes:
- Scenario IDs are generated on-the-fly; the ID from a previous session may no longer resolve. Re-list scenarios with `GET /v1/scenarios`.
- Quest single-fetch (`GET /v1/quests/{id}`) is not yet backed by persistent storage. Use `GET /v1/quests` (list) instead.

### `timeout` (504)

The agent pipeline exceeded its 30-second timeout. Recovery:
- Wait 5 seconds, then retry with the same `Idempotency-Key`.
- If repeated timeouts, the LLM backend may be overloaded. Fall back to cached/fallback scenarios.

### `internal_error` (500)

Unexpected server error. Recovery:
- Retry once with the same `Idempotency-Key`.
- If persistent, check `GET /v1/runtime` to inspect agent state.
- Check `GET /v1/health` to verify the backend is up.

### `invalid_request` (400)

Your request body is malformed. Do not retry. Check:
- Required fields are present (`scenario_id` for quests/actions, `decision` for approvals).
- `decision` must be exactly `"approved"` or `"rejected"`.

## Pagination Pattern

```
page_1 = GET /v1/events?limit=10
if page_1.has_more:
    last_id = page_1.data[-1].id
    page_2 = GET /v1/events?limit=10&starting_after={last_id}
```

Never use offset-based pagination. Only `starting_after` with a resource ID.

## Common Agent Workflow

```
1. GET /v1/health                              # verify server is up
2. GET /v1/scenarios?persona_id=p05            # get available scenarios
3. Pick a scenario_id from the list
4. POST /v1/quests {scenario_id}               # activate quest
   Headers: Idempotency-Key: activate_{scenario_id}
5. GET /v1/approvals                           # check for approval gates
6. POST /v1/approvals/{id}/resolve {decision}  # resolve each gate
7. GET /v1/events?quest={quest_id}&limit=20    # monitor progress
8. POST /v1/messages {messages, scenario}      # chat about the quest
```

## Notion Leads CRM Workflow

```
1. POST /v1/notion/leads/setup
2. POST /v1/notion/leads/sync {leads, strict_reconcile:true}
3. GET /v1/notion/leads?view=today_followups
4. PATCH /v1/notion/leads/{lead_key} {status,next_follow_up_date,...}
5. POST /v1/notion/leads/realtime {action,task_payload} for async edits
```

Known-good Theo sync payload example:

```json
{
  "parent_page_id": "Leads-Tracking-25c74e49e5de8035a901cdd614cb3bf7",
  "database_title": "Theo Client Pipeline",
  "data_source_title": "Theo Leads",
  "database_id": "29b3ec6c4bce42ca9e4628a79466dd53",
  "data_source_id": "5d472424-826f-4719-8ac6-06f0f127e068",
  "strict_reconcile": true,
  "leads": [
    {
      "name": "Austin SaaS Founder - Referral",
      "status": "Contacted",
      "lead_type": "Referral",
      "priority": "High",
      "deal_size": 3200,
      "last_contact": "2026-03-05",
      "next_action": "Send scope options and pricing anchors",
      "next_follow_up_date": "2026-03-07",
      "email_handle": "founder@example.com",
      "source": "Referral",
      "notes": "Warm intro from design meetup. Strong fit for brand + motion."
    },
    {
      "name": "Local Coffee Roaster Website Refresh",
      "status": "Lead",
      "lead_type": "Inbound",
      "priority": "Medium",
      "deal_size": 1800,
      "next_action": "Send first-touch portfolio samples and discovery call link",
      "next_follow_up_date": "2026-03-08",
      "email_handle": "@localroaster",
      "source": "Portfolio",
      "notes": "Inbound from Instagram portfolio post."
    }
  ]
}
```

Schema note for agents:
- `Status` must be a Notion `select` property for current integration compatibility.

## Lead OS Workflow

```
1. POST /v1/notion/leads/os/tick {top_n}
2. GET /v1/notion/leads/os/state
3. POST /v1/notion/leads/os/dispatch {limit,min_score,dry_run}
4. Use /v1/approvals when irreversible customer-facing actions are queued
```

## Figma-to-Lead Workflow

```
1. POST /v1/figma/webhooks  (comment intake)
2. GET /v1/figma/comments/pending
3. POST /v1/figma/comments/{comment_id}/promote-to-lead
4. Continue lead maintenance via /v1/notion/leads/*
```

## Figma Polling Workflow (No Webhooks)

```
1. POST /v1/figma/comments/poll {file_key}
2. GET /v1/figma/comments/pending
3. POST /v1/figma/comments/{comment_id}/promote-to-lead (optional)
4. POST /v1/figma/comments/{comment_id}/prepare-send (optional)
```

## Test Mode

Use `Authorization: Bearer sk_demo_default` to enter test mode. All resources will have `livemode: false`. No real external actions (Composio, calendar, social) are executed. Useful for development and demos.
