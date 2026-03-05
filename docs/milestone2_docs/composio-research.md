# Composio Integration Research

## What is Composio?

**Composio** is an **agentic tool execution framework** that provides:
- Pre-built integrations with 100+ apps (Google, Notion, Facebook, Figma, Slack, etc.)
- Structured actions (READ/WRITE/VERIFY) for each integration
- Entity-based connection management (users authenticate once, agents use connections)
- SDK for programmatic action execution

---

## Current Integration Status (Porthon/Questline)

### ✅ Connected Apps (4)

| App | Connection ID | Status |
|-----|--------------|--------|
| Google Calendar | `5e473532-...` | ✅ Working |
| Notion | `938e6ab0-...` | ⚠️ Partial (parent_id issue) |
| Facebook | `e3105225-...` | ✅ Working |
| Figma | `d2da7794-...` | ✅ Working |

### 📦 Composio Actions Used

#### Google Calendar
- `GOOGLECALENDAR_FREE_BUSY_QUERY` — READ free slots
- `GOOGLECALENDAR_CREATE_EVENT` — WRITE events
- `GOOGLECALENDAR_FIND_EVENT` — VERIFY creation

#### Notion
- `NOTION_SEARCH_NOTION_PAGE` — READ search
- `NOTION_CREATE_NOTION_PAGE` — WRITE (blocked: needs parent_id)
- `NOTION_CREATE_DATABASE` — WRITE
- `NOTION_INSERT_ROW_DATABASE` — WRITE
- `NOTION_QUERY_DATABASE` — READ (not yet wired)

#### Facebook
- `FACEBOOK_GET_PAGE_POSTS` — READ posts
- `FACEBOOK_CREATE_POST` — WRITE drafts
- `FACEBOOK_GET_POST` — READ verification (not yet wired)

#### Figma
- `FIGMA_GET_CURRENT_USER` — READ
- `FIGMA_GET_FILE_JSON` — READ
- `FIGMA_EXTRACT_DESIGN_TOKENS` — READ

---

## Agent Framework Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Master Loop (15min tick)                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Queue Mgmt  │  │ Event Ingest│  │  Dispatch   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   KG Worker   │    │  Calendar     │    │   Notion      │
│               │    │   Worker      │    │   Workers     │
│ • search      │    │ • sync_sched  │    │ • leads       │
│ • classify    │    │ • create_bloc │    │ • opportunity │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                 ┌─────────────────────────┐
                 │   Composio Client       │
                 │   (execute_action)     │
                 └─────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌────────┐           ┌────────┐           ┌────────┐
   │ Google │           │ Notion │           │Facebook│
   │  Cal   │           │        │           │        │
   └────────┘           └────────┘           └────────┘
```

---

## Skill Registry (7 Skills)

| Skill ID | Display Name | Actions | Risk |
|----------|--------------|---------|------|
| `kg-search` | KG Search | search, classify | Low |
| `calendar-scheduler` | Calendar Scheduler | sync_schedule, create_block, move_block | Medium |
| `notion-leads-tracker` | Notion Leads Tracker | create_pipeline, add_lead, search_leads | Low |
| `notion-opportunity-tracker` | Notion Opportunity Tracker | create_workspace, add_progress_page | Low |
| `facebook-publisher` | Facebook Publisher | draft_posts, fetch_comments, draft_comment_reply, schedule_post, publish_post, reply_comment | Low→High |
| `figma-plan-generator` | Figma Plan Generator | generate_challenge, verify_connection, comment_file | Medium |
| `self-improvement-loop` | Self Improvement Loop | log_error, log_learning, log_feature_request, promote_pattern | Low |

---

## Workflow Chaining Possibilities

### 1. **Figma → Facebook (Portfolio Showcase)**
```
FigmaWorker.generate_challenge
    ↓ (extracts design tokens)
FacebookWorker.draft_posts (with Figma screenshots)
    ↓
FacebookWorker.schedule_post
```
**Use case:** Weekly design challenges → social media posts

### 2. **KG Search → Calendar (Context-Aware Scheduling)**
```
KGWorker.search ("What does Theo need this week?")
    ↓ (returns relevant context)
CalendarWorker.sync_schedule (with KG context)
    ↓
Google Calendar events created
```
**Use case:** AI-informed scheduling based on personal patterns

### 3. **Notion → Calendar (Lead Follow-up)**
```
NotionLeadsWorker.search_leads
    ↓ (finds overdue leads)
CalendarWorker.create_block ("Follow-up with Client X")
    ↓
Google Calendar reminder created
```
**Use case:** Automated lead follow-up reminders

### 4. **Facebook Comments → Notion (Social Lead Capture)**
```
FacebookWorker.fetch_comments
    ↓ (detects new interested comment)
NotionLeadsWorker.add_lead (from comment)
    ↓
Notion lead database updated
```
**Use case:** Turn social engagement into leads

### 5. **Multi-Agent Scenario Pipeline**
```
Scenario selected (e.g., "Freelance Stabilization")
    ↓
KGWorker.search (pattern analysis)
    ↓ parallel
CalendarWorker.sync_schedule
NotionLeadsWorker.create_pipeline
NotionOpportunityWorker.create_workspace
FacebookWorker.draft_posts
FigmaWorker.generate_challenge
    ↓
All artifacts generated for scenario
```

---

## Approval-Required Actions (Safety Model)

| Action | Risk | Requires Approval |
|--------|------|-------------------|
| `publish_post` | HIGH | ✅ Yes |
| `reply_comment` | HIGH | ✅ Yes |
| `move_block` | MEDIUM | ✅ Yes |
| `schedule_post` | MEDIUM | ✅ Yes |
| `comment_file` | MEDIUM | ✅ Yes |
| `create_block` | MEDIUM | ✅ Yes |
| Others | LOW | ❌ No |

---

## Demo vs Live Mode

| Mode | Behavior |
|------|----------|
| **Demo** | `PORTTHON_OFFLINE_MODE=1` or `sk_demo_*` auth — returns mock responses |
| **Live** | Real Composio calls → actual Google Calendar events, Notion pages, etc. |

---

## Key Files

- **Client:** `src/backend/integrations/composio_client.py`
- **Workers:** `src/backend/deepagent/workers/`
- **Skills:** `src/backend/deepagent/skills/registry.py`
- **Tests:** `src/backend/tests/test_e2e_composio.py`
- **Status:** `docs/milestone1_docs/COMPOSIO_STATUS.md`

---

## What's Working Now

- ✅ Google Calendar: Free busy query → event creation
- ✅ Facebook: Post drafting, comment replies (draft mode)
- ✅ Figma: User verification, challenge generation
- ⚠️ Notion: Search works, page creation blocked (parent_id)
- ✅ Demo mode: All workers function with mock data

## What's Possible with Real Integrations

1. **Full Notion automation** — workspace pages, databases, row CRUD
2. **Live Facebook posting** — schedule real posts, reply to comments
3. **Real Figma interaction** — extract tokens from real files, post comments
4. **Cross-app workflows** — Figma → Facebook, Notion → Calendar
5. **Outcome verification** — confirm actions completed via READ calls
