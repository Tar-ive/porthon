---
name: self-improvement-loop
description: Capture runtime learnings, failures, and workflow corrections for continuous agent improvement.
---

# Self Improvement Loop

Use this skill to keep the always-on runtime improving over time.

## Actions
- `log_error`
- `log_learning`
- `log_feature_request`
- `promote_pattern`

## Required Inputs
- `action`
- `summary`

## Output
- Structured learning entry id
- Suggested follow-up action

## Guardrails
- Log actionable context, not raw secrets.
- Promote only cross-cutting learnings to durable docs.
