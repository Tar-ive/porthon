# V3 Operations Runbook

See also:
- `V3_CLOUD_DEPLOYMENT_AND_BUDGET.md` for Cloud Run setup, auth posture, monthly cost model, and credit runway.

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
5. Check cloud spend trend, credit runway, and log volume against budget guardrails.

## Incident checks

- If webhook intake seems broken:
  - Verify watcher status and passcode.
  - Validate pending comments endpoint.
  - Confirm dedupe behavior and event history.

- If lead dispatch quality drops:
  - Re-run `tick`.
  - Verify Notion schema and lead normalization.
  - Inspect sustainability snapshot for backlog and lane imbalance.

- If cloud cost spikes:
  - Check Cloud Run vCPU/GiB usage for unexpected scale changes.
  - Inspect Cloud Logging ingestion and exclusions.
  - Review Artifact Registry image retention and Cloud Build minute usage.
  - Recompute runway in `V3_CLOUD_DEPLOYMENT_AND_BUDGET.md`.

## Milestone acceptance checklist

- Lead OS endpoints return deterministic, structured responses.
- Figma comment promotion produces stable lead linkage.
- Pod snapshot reflects runtime queue pressure.
- Sustainability snapshot exposes actionable metrics.
- Existing Notion/Figma regression suite remains green.
