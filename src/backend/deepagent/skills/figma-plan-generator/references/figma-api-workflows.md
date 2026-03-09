# Figma API Workflow Notes (Adapted)

Source adapted from imported `figma-2.1.0` package.

## Useful endpoints for planning
- `GET /v1/files/{key}` for full structure/context
- `GET /v1/files/{key}/components` for reusable inventory
- `GET /v1/files/{key}/styles` for token/style audit
- `GET /v1/images/{key}` for export URLs

## Theo-specific usage
- Build milestone plans from existing components/styles.
- Generate portfolio-worthy deliverables from real frames.
- Feed exports into content workflow as progress artifacts.

## Constraints
- Treat as read-only analysis by default.
- Handle rate limits and retries.
