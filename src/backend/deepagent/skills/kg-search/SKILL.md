---
name: kg-search
description: Retrieve scenario-aware personal context and behavioral patterns from memory/KG for downstream workers.
---

# KG Search

Use this skill when a worker needs grounded personal context before acting.

## Trigger
- Any planning, prioritization, or reflection task that needs evidence.

## Contract
- `intent` enum: `factual|pattern|advice|reflection|emotional`
- `scope` enum: `recent|longitudinal|scenario`
- `query` string: short, specific prompt
- Required: `intent`, `scope`, `query`

## Output
- `snippets`: ranked evidence snippets
- `confidence`: `0.0..1.0`
- `refs`: source references

## Guardrails
- Keep context concise.
- Prefer active-scenario signals when available.

## References
- Read [kg-fact-lifecycle.md](/Users/tarive/porthon/src/backend/deepagent/skills/kg-search/references/kg-fact-lifecycle.md) when implementing updates/supersession behavior.
