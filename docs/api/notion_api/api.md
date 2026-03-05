# Notion API: Deterministic Theo Leads CRM

This guide defines the deterministic Notion CRM flow used by the agent runtime:
- create/reuse the Leads database
- enforce schema
- sync/upsert rows by stable key
- archive stale rows safely
- expose view-style query modes for follow-up operations

It targets Notion API version `2025-09-03` (database + data source model).

## Theo Leads Schema

Database title:
- `Leads`

Data source title:
- `Theo Leads`

Properties:
- `Name` (`title`) - company or person
- `Status` (`select`) - `Lead`, `Contacted`, `Meeting booked`, `Proposal sent`, `Won`, `Lost`
- `Lead type` (`select`) - `Inbound`, `Outbound`, `Referral`, `Previous client`
- `Priority` (`select`) - `High`, `Medium`, `Low`
- `Deal size` (`number`) - expected value / MRR
- `Last contact` (`date`)
- `Next action` (`rich_text`)
- `Next follow-up date` (`date`)
- `Email / handle` (`rich_text`)
- `Source` (`select`)
- `Notes` (`rich_text`)
- `Lead Key` (`rich_text`) - deterministic unique key

Canonical key:
- `lead_key = lower(trim(name)) + "::" + lower(trim(source))`

## Required Headers

```http
Authorization: Bearer <NOTION_TOKEN>
Notion-Version: 2025-09-03
Content-Type: application/json
```

## Step 1: Setup (Create or Reuse)

1. Reuse persisted IDs first (`database_id`, `data_source_id`).
2. Else search existing database by title `Leads`.
3. Else create database under configured parent page.
4. Retrieve database and resolve child `data_source_id`.

```bash
curl -sS https://api.notion.com/v1/databases \
  -X POST \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {"type": "page_id", "page_id": "'"$NOTION_PARENT_PAGE_ID"'"},
    "title": [{"type": "text", "text": {"content": "Leads"}}]
  }'
```

Persist:
- `database_id`
- `data_source_id`
- `schema_version` (`crm_leads_v2`)

## Step 2: Enforce Schema Deterministically

Patch schema every run.

```bash
curl -sS "https://api.notion.com/v1/data_sources/$DATA_SOURCE_ID" \
  -X PATCH \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "title": [{"type":"text","text":{"content":"Theo Leads"}}],
    "properties": {
      "Name": {"title": {}},
      "Status": {"select": {"options": [
        {"name":"Lead"}, {"name":"Contacted"}, {"name":"Meeting booked"},
        {"name":"Proposal sent"}, {"name":"Won"}, {"name":"Lost"}
      ]}},
      "Lead type": {"select": {"options": [
        {"name":"Inbound"}, {"name":"Outbound"}, {"name":"Referral"}, {"name":"Previous client"}
      ]}},
      "Priority": {"select": {"options": [
        {"name":"High"}, {"name":"Medium"}, {"name":"Low"}
      ]}},
      "Deal size": {"number": {"format":"dollar"}},
      "Last contact": {"date": {}},
      "Next action": {"rich_text": {}},
      "Next follow-up date": {"date": {}},
      "Email / handle": {"rich_text": {}},
      "Source": {"select": {}},
      "Notes": {"rich_text": {}},
      "Lead Key": {"rich_text": {}}
    }
  }'
```

## Step 3: Query Rows

```bash
curl -sS "https://api.notion.com/v1/data_sources/$DATA_SOURCE_ID/query" \
  -X POST \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"page_size": 100}'
```

Paginate with `next_cursor` until exhausted.

## Step 4: Deterministic Sync / Upsert

Algorithm:
1. Normalize desired lead payloads.
2. Key both desired and existing rows by `Lead Key`.
3. Create missing rows.
4. Patch changed rows only.
5. If `strict_reconcile=true`, archive rows absent from desired set.

Create row:

```bash
curl -sS https://api.notion.com/v1/pages \
  -X POST \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {"type":"data_source_id","data_source_id":"'"$DATA_SOURCE_ID"'"},
    "properties": {
      "Name": {"title":[{"type":"text","text":{"content":"Referral Lead"}}]},
      "Status": {"select":{"name":"Lead"}},
      "Lead type": {"select":{"name":"Referral"}},
      "Priority": {"select":{"name":"High"}},
      "Deal size": {"number": 1500},
      "Next action": {"rich_text":[{"type":"text","text":{"content":"Send intro scope"}}]},
      "Next follow-up date": {"date":{"start":"2026-03-09"}},
      "Source": {"select":{"name":"Referral"}},
      "Lead Key": {"rich_text":[{"type":"text","text":{"content":"referral lead::referral"}}]}
    }
  }'
```

Archive stale row:

```bash
curl -sS "https://api.notion.com/v1/pages/$PAGE_ID" \
  -X PATCH \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"in_trash": true}'
```

### Production Upload Example (Theo)

Use this `POST /v1/notion/leads/sync` body as a known-good ingestion example:

```json
{
  "parent_page_id": "Leads-Tracking-25c74e49e5de8035a901cdd614cb3bf7",
  "database_title": "Theo Client Pipeline",
  "data_source_title": "Theo Leads",
  "database_id": "29b3ec6c4bce42ca9e4628a79466dd53",
  "data_source_id": "5d472424-826f-4719-8ac6-06f0f127e068",
  "strict_reconcile": true,
  "leads": [
    {
      "name": "Austin SaaS Founder - Referral",
      "status": "Contacted",
      "lead_type": "Referral",
      "priority": "High",
      "deal_size": 3200,
      "last_contact": "2026-03-05",
      "next_action": "Send scope options and pricing anchors",
      "next_follow_up_date": "2026-03-07",
      "email_handle": "founder@example.com",
      "source": "Referral",
      "notes": "Warm intro from design meetup. Strong fit for brand + motion."
    },
    {
      "name": "Local Coffee Roaster Website Refresh",
      "status": "Lead",
      "lead_type": "Inbound",
      "priority": "Medium",
      "deal_size": 1800,
      "next_action": "Send first-touch portfolio samples and discovery call link",
      "next_follow_up_date": "2026-03-08",
      "email_handle": "@localroaster",
      "source": "Portfolio",
      "notes": "Inbound from Instagram portfolio post."
    }
  ]
}
```

Important schema compatibility note:
- `Status` must be a Notion `select` property in this integration version.
- If `Status` is a Notion `status` property, sync will fail with: `Status is expected to be status.`

## Pipeline Views (as API Query Modes)

Notion UI views are represented in API as server-side filters:
- `today_followups`: open status + overdue/today `Next follow-up date`
- `high_value_focus`: open status + `Deal size >= threshold`
- `warm_inbound`: `Lead type in {Inbound, Referral}`
- `prospecting`: `Status=Lead` and empty `Last contact`

## Daily Operating Rhythm (Agent-Compatible)

- Ingestion: create/upsert lead row immediately from inquiry events.
- Morning pass: list `today_followups`, clear queue, set next touch date.
- Prospecting block: list `prospecting`, write `Last contact` and follow-up date.
- Weekly review: archive or reschedule leads with no activity.

## Optional Relations (Future Extension)

When needed, attach relations to:
- `Clients` DB
- `Projects` DB
- `Tasks` DB

Keep leads sync deterministic first, then add rollups for conversion and revenue metrics.

## V3 Lead OS Extensions

Lead OS introduces pod-scheduled execution on top of the same deterministic Notion schema.

Additional operational fields (additive, optional):
- `Lane` (`select`) - `Inbound`, `Referral`, `Outbound`, `Previous client`
- `Owner pod` (`select`) - `intake_pod`, `nurture_pod`, `close_pod`, `finance_pod`
- `Response SLA due` (`date`)
- `Effort estimate (min)` (`number`)
- `Acquisition cost est` (`number`)
- `Conversion confidence` (`number`)

New runtime endpoints:
- `GET /v1/notion/leads/os/state`
- `POST /v1/notion/leads/os/tick`
- `POST /v1/notion/leads/os/dispatch`

Figma conversion endpoint:
- `POST /v1/figma/comments/{comment_id}/promote-to-lead`

This keeps Notion as source-of-truth for lead records while agent pods manage prioritization and dispatch.

## Determinism Rules

- Pin `Notion-Version: 2025-09-03`.
- Persist IDs after setup (`database_id`, `data_source_id`).
- Use `Lead Key` uniqueness contract.
- Sort keys before writes.
- Diff before patching.
- Retry `429` with `Retry-After`.
- Log `created/updated/noop/archived` counts each run.

## References

- https://developers.notion.com/llms.txt
- https://developers.notion.com/reference/database-create
- https://developers.notion.com/reference/update-a-data-source
- https://developers.notion.com/reference/query-a-data-source
- https://developers.notion.com/reference/post-page
- https://developers.notion.com/reference/patch-page
- https://developers.notion.com/reference/request-limits
- https://developers.notion.com/guides/get-started/upgrade-guide-2025-09-03
