---
name: figma-plan-generator
description: Generate scenario-linked Figma practice and delivery plans with milestone outputs.
---

# Figma Plan Generator

Use this skill to keep design execution tied to active scenario goals.

## Trigger
- Scenario activation requiring portfolio or skill growth.
- Weekly planning and milestone refresh.

## Contract
- `action` enum: `generate_plan|derive_milestones|sync_to_content`
- `difficulty` enum: `beginner|intermediate|advanced`
- `scenario_title` string
- Required:
  - `generate_plan`: `action,scenario_title`
  - `derive_milestones`: `action,scenario_title`
  - `sync_to_content`: `action,scenario_title`

## Output
- Challenge set
- Weekly milestones
- Content hooks for social narrative

## Guardrails
- Prefer measurable artifacts over vague learning tasks.
- Keep cadence realistic to current execution level.

## References
- Read [figma-api-workflows.md](/Users/tarive/porthon/src/backend/deepagent/skills/figma-plan-generator/references/figma-api-workflows.md) for endpoint-level planning patterns.
