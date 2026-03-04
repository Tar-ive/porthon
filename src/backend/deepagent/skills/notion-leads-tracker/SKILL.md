---
name: notion-leads-tracker
description: Track inbound leads, stages, and follow-ups in Notion for scenario-driven revenue execution.
---

# Notion Leads Tracker

Use this skill for lead lifecycle operations.

## Trigger
- New lead detected from notes/chat/context.
- Stage updates and follow-up scheduling.

## Contract
- `action` enum: `create_lead|update_stage|log_touchpoint|set_followup`
- `stage` enum: `new|qualified|proposal|negotiation|won|lost`
- `lead_name` string
- `due_date` ISO date (optional)
- Required:
  - `create_lead`: `action,lead_name`
  - `update_stage`: `action,lead_name,stage`
  - `log_touchpoint`: `action,lead_name`
  - `set_followup`: `action,lead_name,due_date`

## Guardrails
- Normalize lead names.
- Stage changes should include next action or follow-up date.

## References
- Read [notion-data-source-notes.md](/Users/tarive/porthon/src/backend/deepagent/skills/notion-leads-tracker/references/notion-data-source-notes.md) for Notion API shape and reliability notes.
