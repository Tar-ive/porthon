# Figma API Integration (OpenAPI-First, No Composio)

This implementation uses [`openapi.yaml`](./openapi.yaml) as the source of truth and maps it to internal `/v1/figma/*` endpoints plus `figma_worker` actions.

## Environment

Required for live mode:

- `FIGMA_API_KEY` (personal access token or OAuth token with comments/webhooks scopes)
- `FIGMA_WEBHOOK_PASSCODE` (optional global default passcode for inbound webhook verification)

Optional:

- `PORTTHON_OFFLINE_MODE=1` or demo auth key (`sk_demo_*`) for deterministic test mode.

Production deployment + cost model:

- See `docs/milestone3_docs/V3_CLOUD_DEPLOYMENT_AND_BUDGET.md` for Cloud Run SSL deployment, webhook ingress posture, and monthly budget/runway forecasting.

## Internal API Surface

Programmatic watcher management:

- `POST /v1/figma/watchers`
- `GET /v1/figma/watchers`
- `PATCH /v1/figma/watchers/{watcher_id}`
- `DELETE /v1/figma/watchers/{watcher_id}`
- `GET /v1/figma/watchers/{watcher_id}/requests`

Inbound webhook:

- `POST /v1/figma/webhooks`

Comment queue / approval pipeline:

- `POST /v1/figma/comments/poll` (poll mode, webhook-free ingestion)
- `GET /v1/figma/comments/pending`
- `POST /v1/figma/comments/{comment_id}/prepare-send`
- `POST /v1/figma/comments/{comment_id}/promote-to-lead`

Back-compat alias:

- `POST /v1/integrations/composio/webhook` (deprecated; forwards into same ingest path)

## Worker Actions

`figma_worker` now supports:

- `verify_connection` (uses `GET /v1/me`)
- `comment_file` (uses `POST /v1/files/{file_key}/comments`)
- `reply_comment` (uses `POST /v1/files/{file_key}/comments` with `comment_id`)
- `process_webhook_event` (normalizes webhook payload and creates a draft follow-up)

Policy:

- `figma_worker.reply_comment` is irreversible and requires explicit approval before execution.

## Deterministic Webhook Handling

`integrations/figma_webhooks.py` normalizes official `FILE_COMMENT` payloads:

- Supports fragment arrays (`comment: [{text|mention}]`) and renders canonical message text.
- Generates stable event IDs / dedupe keys.
- Extracts `comment_id`, `file_key`, actor, timestamps, and passcode.
- Validates passcode before ingesting into `integration.figma.webhook.received`.

## Real-Time Agent Flow

1. A watcher is created for a Figma file (`/v1/figma/watchers`).
2. Figma sends `FILE_COMMENT` webhook to `/v1/figma/webhooks`.
3. Master loop ingests event and runs `figma_worker.process_webhook_event`.
4. Pending item appears in `/v1/figma/comments/pending` with `draft_reply`.
5. Client calls `POST /v1/figma/comments/{comment_id}/prepare-send`.
6. System enqueues `figma_worker.reply_comment` and marks it `awaiting_approval`.
7. Approval is resolved through existing approvals API:
   - `POST /v1/approvals/{approval_id}/resolve` with `decision="approved"` to send.
8. Pending status resolves to `sent` or `failed` based on task execution.

Lead procurement extension:
9. Promote collaboration comment to CRM lead:
   - `POST /v1/figma/comments/{comment_id}/promote-to-lead`
10. Persist mapping:
   - `comment_id -> lead_key`
   - `file_key + actor_handle -> lead_key` for continuity on future comments.

Webhook-free polling flow:
1. Call `POST /v1/figma/comments/poll` with `file_key`.
2. Endpoint fetches `/v1/files/{file_key}/comments` from Figma in live mode.
3. New comments are normalized and ingested into `integration.figma.webhook.received`.
4. Processed items appear in `GET /v1/figma/comments/pending`.

## Programmatic Setup Example

Using Questline API (recommended for unified runtime + approvals):

```bash
curl -X POST http://localhost:8000/v1/figma/watchers \
  -H "Authorization: Bearer sk_live_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "file_key": "AbCdEf123",
    "endpoint": "https://your.api/v1/figma/webhooks",
    "event_type": "FILE_COMMENT",
    "passcode": "replace-me",
    "context": "file"
  }'
```

Then configure the same endpoint/passcode in Figma webhook settings (or let the live endpoint create the webhook via Figma API automatically).

Direct Figma API setup (v2 webhook create):

```bash
curl -X POST "https://api.figma.com/v2/webhooks" \
  -H "X-Figma-Token: <YOUR_PERSONAL_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "file_key": "<FILE_KEY>",
    "endpoint": "https://your-domain.com/figma-webhook",
    "event_type": "FILE_COMMENT",
    "passcode": "<YOUR_RANDOM_SECRET>",
    "description": "Notify on file comments",
    "context": "file",
    "context_id": "<FILE_KEY>",
    "status": "ACTIVE"
  }'
```
