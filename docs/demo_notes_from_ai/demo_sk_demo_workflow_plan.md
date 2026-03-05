# sk_demo Workflow Implementation Plan

## Scope
- Demo key family: `sk_demo_*`
- Two workflows only:
  - Proactive quest workflow (deterministic preview + optional live commit)
  - Live Facebook comment-watch workflow (polling + reply draft)

## Canonical ID Prefixes
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

## Mode Behavior
- `sk_demo_*`:
  - deterministic scenarios/actions/artifacts for Theo (`p05`)
  - `livemode: false`
  - `/v1/messages` remains OpenAI-backed
- `sk_live_*`:
  - retained for live integrations

## Additive API Fields
- `cycle_end.payload.cycle_duration_ms`
- `POST /v1/quests` response `activation_duration_ms`
- `GET /v1/runtime` optional:
  - `demo_artifacts`
  - `value_signals`
  - `workflow_state`

## Workflow 1: Proactive Quest
Deterministic demo scenarios:
- `scen_001`: Conversion-First Freelance Stabilization
- `scen_002`: Austin Creative Reputation Flywheel
- `scen_003`: Sustainable ADHD-Compatible Studio Path

1. Quest activation seeds deterministic preview artifacts:
  - Calendar: 2 deep-work blocks (UT Library), 1 invoice admin block, 1 debt review
  - Notion Leads: Client Pipeline with 3 leads
  - Notion Opportunity: Questline workspace + progress page
  - Figma: challenge briefs + milestones
2. Event `demo.workflow.proactive.preview` refreshes preview artifacts.
3. Event `demo.workflow.proactive.commit` enqueues live commit tasks:
  - Calendar event creation
  - Notion pipeline/workspace setup
  - Optional Figma file comment (if `figma_file_key` provided)

## Workflow 2: Facebook Comment Watch
1. Event `demo.workflow.facebook_watch.start` stores watch config.
2. Event `demo.workflow.facebook_watch.poll`:
  - polls page posts
  - polls comments by post
  - detects unseen `comment_id`s
  - drafts reply text (OpenAI with deterministic fallback)
  - stores pending replies as `ready_to_send`
3. Event `demo.workflow.facebook_watch.inject` supports deterministic/manual fallback comments.

## Composio Capability Notes (researched)
- Facebook toolkit actions used:
  - `FACEBOOK_GET_PAGE_POSTS`
  - `FACEBOOK_GET_COMMENTS`
  - `FACEBOOK_GET_COMMENT`
  - `FACEBOOK_CREATE_COMMENT`
- Trigger catalog check: no native Facebook trigger types available currently.
- Therefore comment-watch is polling-based in this implementation.
- Optional Figma write path uses `FIGMA_ADD_A_COMMENT_TO_A_FILE`.

## State/Runtime Safety
- Auto-heal missing or empty `workers`, `budgets`, `circuits` on state load.
- Keep deterministic defaults for stale runtime files.

## Test Focus
- Fast suite avoids repeated TestClient startup via session-scoped fixture.
- Validate new additive timing fields.
- Validate demo runtime artifacts presence.
- Validate Facebook watch inject path creates pending reply drafts.
