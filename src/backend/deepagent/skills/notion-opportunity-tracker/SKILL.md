---
name: notion-opportunity-tracker
description: Track opportunity value, probability, and closure outcomes in Notion.
---

# Notion Opportunity Tracker

Use this skill for revenue opportunities and forecast quality.

## Trigger
- Opportunity creation from qualified leads.
- Probability/amount updates after client interactions.
- Closure events.

## Contract
- `action` enum: `create_opportunity|update_probability|attach_next_action|close_won|close_lost`
- `opportunity_name` string
- `probability_bucket` enum: `0_10|11_30|31_60|61_80|81_100`
- `value_usd` number (optional)
- Required:
  - `create_opportunity`: `action,opportunity_name`
  - `update_probability`: `action,opportunity_name,probability_bucket`
  - `attach_next_action`: `action,opportunity_name`
  - `close_won`: `action,opportunity_name`
  - `close_lost`: `action,opportunity_name`

## Guardrails
- Keep probability explicit and bounded.
- On `close_lost`, attach reason for learning loop.

## References
- Read [notion-forecast-notes.md](/Users/tarive/porthon/src/backend/deepagent/skills/notion-opportunity-tracker/references/notion-forecast-notes.md) for schema stability patterns.
