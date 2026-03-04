---
name: facebook-publisher
description: Draft and schedule scenario-aligned Facebook posts with approval gating for high-impact actions.
---

# Facebook Publisher

Use this skill for social content drafting and scheduling.

## Trigger
- Milestone completion.
- Weekly narrative summary.
- Scenario progress update.

## Contract
- `action` enum: `draft_post|schedule_post|publish_post|cancel_post`
- `post_type` enum: `milestone|learning_in_public|portfolio|personal_brand`
- `content` string
- `scheduled_time` unix timestamp (for scheduling)
- Required:
  - `draft_post`: `action,content`
  - `schedule_post`: `action,content,scheduled_time`
  - `publish_post`: `action,content`
  - `cancel_post`: `action`

## Risk Class
- Low: `draft_post`
- Medium: `schedule_post`
- High: `publish_post` (approval required)

## Guardrails
- Default to draft-first if confidence is low.
- Avoid repetitive messaging across adjacent posts.

## References
- Read [graph-api-ops.md](/Users/tarive/porthon/src/backend/deepagent/skills/facebook-publisher/references/graph-api-ops.md) for permission and endpoint specifics.
