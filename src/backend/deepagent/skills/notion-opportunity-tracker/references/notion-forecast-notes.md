# Notion Opportunity Forecast Notes (Adapted)

Source adapted from imported `notion-1.0.0` skill package.

## Suggested properties
- `Name` (title)
- `Stage` (select)
- `Probability` (select/number)
- `Value` (number)
- `Next Action` (rich text)
- `Updated` (date)

## Reliability rules
- Keep property names stable across cycles.
- Avoid writing unsupported property types from free-form LLM output.
- Normalize to minimal schema before create/update.
