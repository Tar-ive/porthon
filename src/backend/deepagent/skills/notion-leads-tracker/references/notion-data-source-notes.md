# Notion Data Source Notes (Adapted)

Source adapted from imported `notion-1.0.0` skill package.

## Versioning
- Always send `Notion-Version` header.

## Data source model
- Query data using `POST /v1/data_sources/{id}/query`.
- Create page rows under database parent using `database_id`.

## Leads tracker reliability rules
- Ensure valid writable `parent_id` before create.
- Keep a required title property in schemas.
- On schema failure, fall back to minimal known-good schema.
