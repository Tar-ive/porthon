# V3 API and Agent Contract

## New endpoints

- `GET /v1/notion/leads/os/state`
- `POST /v1/notion/leads/os/tick`
- `POST /v1/notion/leads/os/dispatch`
- `POST /v1/figma/comments/{comment_id}/promote-to-lead`

## Existing endpoint interplay

- Notion deterministic CRM:
  - `POST /v1/notion/leads/setup`
  - `POST /v1/notion/leads/sync`
  - `GET /v1/notion/leads`
  - `PATCH /v1/notion/leads/{lead_key}`
  - `POST /v1/notion/leads/realtime`

- Figma collaboration loop:
  - `POST /v1/figma/webhooks`
  - `GET /v1/figma/comments/pending`
  - `POST /v1/figma/comments/{comment_id}/prepare-send`

## Agent contract

- Agents must treat `lead_key` as stable identity.
- Agents should use `tick` before `dispatch` for fresh prioritization.
- Promotion from Figma should preserve lead continuity via mapping keys.
- Customer-facing sends continue through approvals for trust-first compliance.

## Compatibility

- No breaking changes to existing Notion/Figma routes.
- V3 additions are additive and backward-compatible.
