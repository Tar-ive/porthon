# V3 Governance and Sustainability

## Governance stance

Trust-first policy:
- Irreversible customer-facing actions require explicit approval.
- Agent autonomy is allowed for reversible CRM maintenance actions.
- All dispatches and approvals remain auditable in runtime state.

## Sustainability dimensions

Customer sustainability:
- Follow-up quality and response timing.
- Context continuity over repeated conversations.
- Avoiding over-contact and message fatigue.

Business sustainability:
- Weighted pipeline value.
- Acquisition cost profile by lane.
- Overdue follow-up backlog.
- Outbound share vs trust-first share.

## Core V3 metrics

- `expected_pipeline_value`
- `weighted_pipeline_value`
- `estimated_acquisition_cost`
- `followup_overdue_count`
- `outbound_share`
- `trust_first_share`
- `efficiency_ratio`

## Decision rules

- When overdue backlog rises, prioritize nurture/close before net-new prospecting.
- When outbound share rises beyond threshold, throttle outbound tasks and rebalance toward referral/inbound lanes.
- When weighted pipeline weakens, prioritize high-confidence and proposal-stage actions.
