# ClawHub Skill Enhancement Notes

## Sources reviewed
- ClawHub command docs: https://docs.openclaw.net/hub/quick-start#manage-skills
- ClawHub security notes: https://docs.openclaw.net/hub/security
- OpenClaw skills docs index: https://docs.openclaw.net/

## Enhancements applied
- Standardized each backend skill contract around enum-first actions and minimal required fields.
- Added explicit risk classification and approval implications to high-impact skills.
- Added machine-readable skill registry in backend (`deepagent/skills/registry.py`) for runtime and UI introspection.
- Added API endpoint `GET /api/agent/skills` so frontend can render skill map/contracts.
- Extended agent map UI to show available skills and action counts.
- Imported and adapted zipped skill packs placed in `src/backend/deepagent/skills/*.zip`:
  - `knowledge-graph-1.0.0.zip` -> KG fact lifecycle reference
  - `notion-1.0.0.zip` -> data source/reliability references for leads/opportunities
  - `facebook-page-manager-1.0.0.zip` -> graph API permission/operation reference
  - `figma-2.1.0.zip` -> endpoint-level planning/export workflow reference
  - `self-improving-agent-1.0.11.zip` -> new `self-improvement-loop` skill contract
- Added env-gated live KG integration test and make target:
  - `tests/live/test_live_kg.py`
  - `make test-live-kg`

## Why this aligns with ClawHub conventions
- Skills are modular with clear trigger/use instructions in `SKILL.md`.
- Contracts are concise and deterministic (token-efficient, easier tool routing).
- High-risk actions are called out and separated from low-risk routines.
