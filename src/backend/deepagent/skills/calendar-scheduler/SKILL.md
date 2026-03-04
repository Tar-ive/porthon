---
name: calendar-scheduler
description: Plan and manage scenario-aligned calendar blocks with conflict checks and ADHD-aware cadence.
---

# Calendar Scheduler

Use this skill for schedule planning, conflict handling, and low-friction execution blocks.

## Trigger
- New scenario activation.
- Weekly/daily re-plan cycles.
- Calendar conflict or slip detection.

## Contract
- `action` enum: `create_block|move_block|cancel_block|check_conflict`
- `priority` enum: `low|medium|high`
- `start_time` ISO datetime
- `end_time` ISO datetime
- `title` string
- Required:
  - `create_block`: `action,start_time,end_time,title`
  - `move_block`: `action,start_time,end_time,title`
  - `cancel_block`: `action,title`
  - `check_conflict`: `action,start_time,end_time`

## Risk Class
- Low: `check_conflict`
- Medium: `create_block`, `move_block`
- High: `cancel_block` for recurring/long blocks (approval may apply)

## Guardrails
- Avoid overlaps and duplicate blocks.
- Prefer short, actionable blocks when confidence is low.
