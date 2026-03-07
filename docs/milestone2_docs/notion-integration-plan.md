# Notion Integration Plan

## Overview

Integrate Notion with the Questline AI agent to create personalized workspaces, lead databases, and task trackers for Theo.

## Setup Required

### 1. Notion Integration
- **Secret:** Set `NOTION_INTEGRATION_SECRET` in `.env`
- **Permissions:** Need to share pages/databases with the integration

### 2. Configuration
Add to `.env`:
```
NOTION_INTEGRATION_SECRET=<your-secret>
NOTION_PARENT_PAGE_ID=<your-notion-page-id>
NOTION_LEADS_DB_ID=<leads-database-id>
NOTION_OPPORTUNITIES_DB_ID=<opportunities-database-id>
```

## Demo Workflow

### Scenario: "Conversion-First Freelance Stabilization"

When activated, the agent will:

1. **Create Client Pipeline Database** (if not exists)
   - Properties: Name, Source, Status, Value, Contact, Notes
   - Status options: Lead → Proposal → Negotiation → Won → Lost

2. **Create Opportunity Workspace**
   - Page with scenario context
   - Progress tracking

3. **Add Leads from Theo's Data**
   - Referral Lead
   - Portfolio Lead  
   - Direct Lead

4. **Track Tasks**
   - Task database for scenario actions

## Available Worker Actions

| Action | Description | Example |
|--------|-------------|---------|
| `create_leads_database` | Create client pipeline DB | Creates with status/source/value fields |
| `create_opportunity_workspace` | Create workspace page | Scenario-specific workspace |
| `add_lead` | Add lead to database | Name, source, value, status |
| `add_opportunity` | Add opportunity | Stage, value, close date |
| `query_leads` | Query leads | Get all leads with filters |
| `create_tracker` | Create task tracker | General task page |

## Triggering from Frontend

### Method 1: Chat Interface
```
POST /v1/messages
Authorization: Bearer sk_demo_default
{
  "messages": [{"role": "user", "content": "Create a lead for Test Client"}]
}
```

### Method 2: Direct Event
```
POST /v1/events
Authorization: Bearer sk_demo_default
{
  "type": "worker.execute",
  "enqueue": true,
  "payload": {
    "worker_id": "notion_creator_worker",
    "action": "add_lead",
    "task_payload": {
      "name": "Test Client",
      "source": "Referral",
      "value": 500
    }
  }
}
```

### Method 3: Scenario Activation
When a scenario activates, the workflow runs automatically:
- Creates Notion workspace
- Populates leads from persona data
- Sets up tracking

## Files Created

- `src/backend/integrations/notion_api.py` - Notion SDK wrapper
- `src/backend/deepagent/workers/notion_creator_worker.py` - Worker with actions

## Notion Cookbook Reference

Based on https://github.com/makenotion/notion-cookbook

Examples:
- `intro-to-notion-api/basic/1-add-block.ts` - Add blocks
- `intro-to-notion-api/intermediate/1-create-a-database.ts` - Create DB
- `intro-to-notion-api/intermediate/2-add-page-to-database.ts` - Add to DB

## Next Steps

1. Get NOTION_PARENT_PAGE_ID from a Notion page
2. Share that page with the integration
3. Test creating a database
4. Wire into scenario activation
