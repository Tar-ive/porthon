# Hyperfocus Attention Block Workflow (Composio + Google Calendar)

## Goal
Create reliable, low-friction hyperfocus blocks that avoid collisions, avoid duplicates, and use Google Calendar native Focus Time semantics.

## Composio Action Mapping
- `GOOGLECALENDAR_FREE_BUSY_QUERY`:
  - Used to check exact-window conflicts before creating blocks.
- `GOOGLECALENDAR_CREATE_EVENT`:
  - Primary payload shape: `start_datetime` + duration fields.
  - Focus block payload adds `eventType: "focusTime"` and `focusTimeProperties`.
- `GOOGLECALENDAR_FIND_EVENT`:
  - Used before create for duplicate protection and after create for verification.

## Solidified Workflow
1. Validate requested block window (`start_time`, `end_time`).
2. Run `FREE_BUSY_QUERY` for the exact interval.
3. If busy and `allow_conflict` is not true, stop with conflict details.
4. Run `FIND_EVENT` with title; if same title + start window exists, skip create.
5. Build create payload:
   - Primary (docs-aligned):
     - `summary`, `description`, `start_datetime`
     - `event_duration_hour`, `event_duration_minutes`
     - `time_zone`, `calendar_id`
     - For hyperfocus: `eventType="focusTime"` + `focusTimeProperties`
   - Legacy fallback:
     - `summary`, `description`, `start_datetime`, `end_datetime`, `timezone`, `calendar_id`
6. Execute create with primary payload first.
7. If Composio returns schema error, retry once with legacy payload.
8. Run `FIND_EVENT` again to verify block discoverability.
9. Return external calendar link and payload variant used (`primary` or `legacy`).

## Hyperfocus Defaults
For focus-time events, use:
- `focusTimeProperties.autoDeclineMode = "declineOnlyNewConflictingInvitations"`
- `focusTimeProperties.chatStatus = "doNotDisturb"`

These defaults protect attention while avoiding destructive changes to existing invitations.
