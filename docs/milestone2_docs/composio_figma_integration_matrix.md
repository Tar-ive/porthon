# Composio Figma Integration Matrix

## SDK Surface in This Repo
- Installed package: `composio-core==0.7.21`
- Client collections used:
  - `Composio().apps`
  - `Composio().actions`
  - `Composio().triggers`

## Figma Actions Used by Deepagent
| Worker action | Composio action | Mode | Notes |
|---|---|---|---|
| `verify_connection` | `FIGMA_GET_CURRENT_USER` | read | Checks account connectivity |
| `generate_challenge` | (LLM-only in worker, optional Figma context read) | read | Uses KG + optional Figma user context |
| `comment_file` | `FIGMA_ADD_A_COMMENT_TO_A_FILE` | write_reversible | Used for proactive commit milestone comment |
| `process_webhook_event` | none (event processing) | read | Handles webhook payload + LLM summaries |

## Reactive Transport
- Primary: webhook ingestion endpoint `POST /v1/integrations/composio/webhook`
- Internal event fan-in: `integration.figma.webhook.received`
- Workflow events: `demo.workflow.figma_watch.start`, `demo.workflow.figma_watch.stop`

## Security
- Irreversible actions require approval (`policy_blocked_action` emitted).
- Webhook secret validation via `COMPOSIO_WEBHOOK_SECRET` and `X-Composio-Webhook-Secret` header.

## Trigger/Tooling References
- Figma toolkit docs: https://docs.composio.dev/toolkits/figma
- Trigger/webhook subscription docs: https://docs.composio.dev/triggers-and-webhooks/subscribing-to-events
- Trigger type catalog API: https://reference.composio.dev/api-reference/api-reference/trigger-types/list-all-trigger-types

## Operational Note
- Full account-specific trigger catalog could not be enumerated in this environment because `COMPOSIO_API_KEY` is not set.
- To verify exact Figma trigger names, run a key-authenticated trigger-type listing filtered to `toolkit_slugs=figma`.
