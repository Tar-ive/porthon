# Skeleton Restructuring Plan (Deep-Agent Style)

## Intent
Restructure backend into a clean shell inspired by deep-agent patterns: separated API routes, stateful runtime service, worker/skill boundaries, and explicit approval/streaming interfaces.

## Target Backend Layout

```text
src/backend/
  app/
    api/
      routes_agent.py
      routes_chat.py
      routes_scenarios.py
      routes_outcomes.py
    deps.py
  deepagent/
    factory.py
    session.py
    loop.py
    dispatcher.py
    approval.py
    stream.py
    workers/
      base.py
      calendar_worker.py
      notion_leads_worker.py
      notion_opportunity_worker.py
      facebook_worker.py
      figma_worker.py
      kg_worker.py
    skills/
      kg-search/SKILL.md
      calendar-scheduler/SKILL.md
      notion-leads-tracker/SKILL.md
      notion-opportunity-tracker/SKILL.md
      facebook-publisher/SKILL.md
      figma-plan-generator/SKILL.md
  state/
    models.py
    store.py
    checkpoints.py
  integrations/
    composio_client.py
  tests/
    fast/
    live/
```

## Migration Strategy
1. Add new modules as shell without breaking existing endpoints.
2. Introduce runtime state store + models.
3. Add new agent APIs (`/api/agent/*`).
4. Wrap legacy `agents/*` behavior behind new worker interfaces.
5. Split tests into fast/live.
6. Keep old orchestration paths for backward compatibility during transition.

## Key Compatibility Constraints
- Preserve `main.py` external behavior while incrementally routing to new modules.
- Preserve composio connectivity via compatibility wrapper.
- Preserve current frontend scenario/chat flow and add agent map as additive UI.

## Runtime Contracts
- `ActiveScenarioState`
- `WorkerTask`
- `WorkerBudget`
- `WorkerCircuitState`
- `ApprovalRequest`
- `CycleSnapshot`
- `AgentRuntimeState`

## Risk Mitigation
- Do not remove legacy files during shell build.
- Ensure new defaults are dry-run safe.
- Add endpoint contract tests before wiring frontend.


- Also need to delete the old agents as they might cause confusions