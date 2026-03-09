# KG Fact Lifecycle (Adapted)

Source adapted from imported `knowledge-graph-1.0.0` skill package.

## Core pattern
- Facts are append-only.
- Old facts are superseded, not deleted.
- Entity summaries are regenerated from active facts.

## Suggested record model
- `id`: stable incrementing id
- `fact`: atomic statement
- `category`: controlled category label
- `timestamp`: ISO date/time
- `source`: origin (`conversation`, `api`, `manual`)
- `status`: `active|superseded`
- `supersededBy`: nullable id

## Runtime guidance for Theo
- Preserve trajectory history for explainability.
- Prefer supersede when goals or constraints change.
- Keep summary generation deterministic and short.
