# V3 Operations Runbook

## Daily rhythm

1. Morning: run Lead OS tick, review top recommendations.
2. Clear overdue follow-ups first.
3. Dispatch top actions in focused blocks.
4. Use Figma promotion flow for collaboration-driven leads.

## Weekly rhythm

1. Review stale leads and close/reschedule.
2. Inspect lane distribution and outbound share.
3. Tune dispatch thresholds (`min_score`, `limit`) as needed.
4. Check approval queue latency for customer-facing actions.

## Incident checks

- If webhook intake seems broken:
  - Verify watcher status and passcode.
  - Validate pending comments endpoint.
  - Confirm dedupe behavior and event history.

- If lead dispatch quality drops:
  - Re-run `tick`.
  - Verify Notion schema and lead normalization.
  - Inspect sustainability snapshot for backlog and lane imbalance.

## Milestone acceptance checklist

- Lead OS endpoints return deterministic, structured responses.
- Figma comment promotion produces stable lead linkage.
- Pod snapshot reflects runtime queue pressure.
- Sustainability snapshot exposes actionable metrics.
- Existing Notion/Figma regression suite remains green.
