# Test Mode Setup

## What Is Test Mode?

Test mode lets you exercise the full API without triggering real external actions (Composio tool calls, calendar writes, social media posts, Notion updates). Any request authenticated with a `sk_test_*` key runs in test mode.

## How to Activate

Pass the test key in the Authorization header:

```
Authorization: Bearer sk_test_demo
```

Every resource returned will include `"livemode": false`.

## Available Test Keys

| Key | Purpose |
|-----|---------|
| `sk_test_demo` | General demo and development use |

Any string matching the pattern `sk_test_*` activates test mode. You can use `sk_test_anything` for your own sessions.

## What Changes in Test Mode

| Feature | Live Mode | Test Mode |
|---------|-----------|-----------|
| `livemode` field | `true` | `false` |
| Scenario generation | LLM-generated from real data | LLM-generated (same), falls back to deterministic |
| Quest activation | Full worker dispatch | Workers seeded but external calls stubbed |
| Approvals | Real approval gates | Same gates, but approved actions are no-ops externally |
| Events | Real event history | Same event history, no external side effects |
| Chat / Messages | Full LLM chat | Same LLM chat |
| Knowledge Graph | Active if Neo4j configured | Same behavior |

## Test Composio Accounts

For live integration tests (`make test-live`), you need real Composio credentials:

1. Create a Composio account at [composio.dev](https://composio.dev)
2. Set in `.env`:
   ```
   COMPOSIO_API_KEY=your_key_here
   ```
3. Connect integrations (Google Calendar, Notion, Figma, Facebook) through the Composio dashboard
4. Run `make test-live` to verify connections

For the Swagger demo, you do NOT need Composio credentials. `sk_test_demo` bypasses external service calls.

## Environment Variables for Test Mode

Minimal `.env` for a working demo:

```bash
# LLM (required for scenario/action generation)
OPENAI_API_KEY=sk-...
# or use OpenRouter:
LLM_BINDING_API_KEY=sk-or-v1-...
LLM_BINDING_HOST=https://openrouter.ai/api/v1
LLM_MODEL=anthropic/claude-sonnet-4

# Optional: Knowledge Graph
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=password
# QDRANT_URL=http://localhost:6333

# Optional: Composio (only for make test-live)
# COMPOSIO_API_KEY=...
```

## How to Verify Test Mode Is Active

```bash
curl http://localhost:8000/v1/health \
  -H "Authorization: Bearer sk_test_demo"
```

Check that the response includes `"livemode": false`.

## Differences from Live Mode for Reviewers

When presenting the demo, clarify:
- "We are in test mode -- the `sk_test_demo` key means no real calendar events, social posts, or Notion updates are created."
- "The same API calls with a `sk_live_` key would execute real actions through Composio integrations."
- "The approval flow still works identically -- you still approve or reject, but the downstream effect is stubbed."
