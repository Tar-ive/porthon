# V3 Lead OS Architecture

## Scheduling model

Treat each lead as a process control block (`lead_pcb`) managed by a pod scheduler in the existing `AlwaysOnMaster` runtime.

Each `lead_pcb` tracks:
- stage/status
- lane
- owner pod
- deal size
- conversion confidence
- trust risk
- effort estimate
- acquisition cost estimate
- follow-up timing and overdue status

## Pod topology (subregions)

- `intake_pod`: ingestion and classification.
- `nurture_pod`: follow-up cadence and relationship continuity.
- `close_pod`: meeting/proposal progression.
- `finance_pod`: sustainability and mix guardrails.

Pods are in-process schedulers backed by existing worker queue and policy controls.

## Runtime behavior

- `tick`: reconcile latest lead set into `lead_pcb` and recompute recommendations.
- `state`: expose pods, recommendations, and sustainability snapshot.
- `dispatch`: enqueue top actions to `notion_leads_worker` deterministically.

## Figma integration behavior

- Webhook comments are normalized and queued as pending collaboration items.
- Promotion endpoint converts a comment into a lead and persists comment↔lead and actor+file↔lead mappings.
- Future comments from mapped actor+file can carry the same lead linkage.
