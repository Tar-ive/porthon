# Notion Integration Guide

## Overview

Questline integrates with Notion to create client pipelines, track leads, and manage scenario workspaces. Uses the official [notion-client](https://github.com/ramnes/notion-sdk-py) Python SDK.

---

## Setup

### 1. Create Notion Integration

1. Go to: https://www.notion.so/my-integrations
2. Click **+ New integration**
3. Name it "Questline" or similar
4. Copy the **Internal Integration Secret**

### 2. Add to .env

```bash
NOTION_INTEGRATION_SECRET=secret_you_just_copied
```

### 3. Share Pages with Integration

1. Create or find a page in Notion (e.g., "Questline")
2. Click **...** (three dots) on the page
3. Scroll down and click **Add connections**
4. Select your integration

---

## API Reference

### Initialization

```python
from integrations.notion_api import get_notion_api

notion = get_notion_api()
```

### Create a Page

```python
result = notion.create_page(
    title="My New Page",
    content=["Line 1", "Line 2"]
)
# Returns: {"id": "...", "url": "https://notion.so/..."}
```

### Create Client Pipeline

```python
pipeline = notion.create_client_pipeline(
    title="Theo Client Pipeline"
)
```

### Add a Lead

```python
lead = notion.add_lead(
    pipeline_page_id="page_id_from_pipeline",
    lead_name="John's Coffee Shop",
    status="Proposal Sent",
    value=1500,
    source="Referral",
    notes="Met at networking event"
)
```

### Create Scenario Page

```python
scenario = notion.create_scenario_page(
    scenario_title="Conversion-First Freelance Stabilization",
    goals=[
        "Make freelancing full-time",
        "Build design portfolio",
        "Pay off $6k debt"
    ],
    challenges=[
        "Week 1: Brief + concepts",
        "Week 2: Mid-fidelity",
        "Week 3: Final polish"
    ]
)
```

---

## Demo Workflow

### Theo's Client Pipeline

Based on Theo's personal profile (freelance designer):

```python
# 1. Create main pipeline
pipeline = notion.create_client_pipeline("Theo Client Pipeline")

# 2. Add leads from his data
leads = [
    {"name": "Referral Lead", "status": "Proposal", "value": 1500, "source": "Referral"},
    {"name": "Portfolio Lead", "status": "Lead", "value": 2500, "source": "Portfolio"},
    {"name": "Direct Lead", "status": "Lead", "value": 3000, "source": "Direct"},
]

for lead in leads:
    notion.add_lead(
        pipeline_page_id=pipeline["id"],
        lead_name=lead["name"],
        status=lead["status"],
        value=lead["value"],
        source=lead["source"]
    )
```

---

## Triggering from API

### Via Events

```bash
curl -X POST http://localhost:8000/v1/events \
  -H "Authorization: Bearer sk_demo_default" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "notion.create_pipeline",
    "payload": {
      "title": "Theo Client Pipeline"
    }
  }'
```

### Via Chat

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Authorization: Bearer sk_demo_default" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Create a lead for Test Client"}]
  }'
```

---

## Notion API Reference

### Official Resources

| Resource | URL |
|----------|-----|
| **Main Docs** | https://developers.notion.com |
| **Python SDK** | https://github.com/ramnes/notion-sdk-py |
| **API Reference** | https://developers.notion.com/reference/intro |
| **Notion Cookbook** | https://github.com/makenotion/notion-cookbook |

### Key Endpoints

- `POST /v1/pages` - Create a page
- `GET /v1/pages/{id}` - Get a page
- `POST /v1/databases` - Create a database
- `GET /v1/databases/{id}` - Query a database
- `POST /v1/blocks/{id}/children` - Add blocks to a page
- `POST /v1/search` - Search pages

### Limitations

- Cannot create top-level files (must use existing page as parent)
- Database creation requires specific property schemas
- Rate limits: 3 requests per second

---

## Files

- `src/backend/integrations/notion_api.py` - Main API wrapper
- `src/backend/deepagent/workers/notion_creator_worker.py` - Worker actions

---

## Current Status

| Feature | Status |
|---------|--------|
| Create pages | ✅ Working |
| Create hierarchies | ✅ Working |
| Add leads | ✅ Working |
| Create scenario pages | ✅ Working |
| Create databases | ⚠️ Limited (SDK quirks) |
| Query databases | ⚠️ Limited |
