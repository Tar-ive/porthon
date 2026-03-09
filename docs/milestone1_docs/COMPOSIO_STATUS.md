# Composio Deep Agents — Implementation Status

**Date:** 2026-03-03
**Branch:** milestone2_tarive
**Persona:** Theo Nakamura (p05) — Freelance Graphic Designer, Austin TX

---

## What Was Done

### 1. Fixed the Composio SDK integration (`composio_tools.py`)

**Problem:** The original code called `_composio.tools.execute()` which doesn't exist in the SDK.

**Fix:** Rewrote to use the correct API:
```python
from composio import Composio, Action
c = Composio(api_key=key)
result = c.actions.execute(action=Action.XXX, params={...}, entity_id='default', connected_account=conn.id)
```

**New features:**
- Caches the `Composio` client and all 4 connection IDs on init
- Auto-infers the connected account from the action name prefix (e.g. `GOOGLECALENDAR_*` → googlecalendar connection)
- Graceful dry-run if no API key or no connection for that app
- Backwards-compatible with old `arguments=` kwarg

**All 4 connections verified active:**
| App | Connection ID |
|-----|--------------|
| googlecalendar | 5e473532-4ba6-47f5-9e02-a89eb946d0c0 |
| notion | 938e6ab0-549f-4103-ad09-cebab9966902 |
| facebook | e3105225-fc11-449d-90dd-668ce629ef97 |
| figma | d2da7794-ff9e-4f63-8e8e-70e0923cccb2 |

---

### 2. Upgraded CalendarCoach (`calendar_coach.py`)

**Composio actions used:**
- `GOOGLECALENDAR_FREE_BUSY_QUERY` (**READ**) — fetches real busy/free slots before the LLM plans
- `GOOGLECALENDAR_CREATE_EVENT` (**WRITE**) — creates actual calendar events
- `GOOGLECALENDAR_FIND_EVENT` (**VERIFY**) — used by outcome collector to confirm creation

**New behavior:**
1. Queries FreeBusy for next week → parses busy windows
2. Passes available slot summary to LLM prompt ("Monday: 10h free 9AM–9PM")
3. LLM generates events using ISO datetime strings (`2026-03-09T09:00:00`)
4. Focus blocks use `eventType: "focusTime"` (Google's native focus time)
5. Per-agent timeout bumped to 120s in orchestrator (OpenRouter needs it)

**Test result:** 12/12 events created in Google Calendar ✓

---

### 3. Upgraded FigmaLearning (`figma_learning.py`)

**Composio actions used:**
- `FIGMA_GET_CURRENT_USER` (**READ**) — verifies connection, gets user handle
- `FIGMA_GET_FILE_JSON` (**READ**) — analyzes existing files if file_key available
- `FIGMA_EXTRACT_DESIGN_TOKENS` (**READ**) — extracts color/typography system

**New behavior:**
1. Calls `FIGMA_GET_CURRENT_USER` first → surfaces real Figma identity into the LLM prompt
2. Attempts to find `.fig` file keys in Theo's `files_index.jsonl` data
3. If found: extracts design tokens + file structure to calibrate challenge difficulty
4. Gracefully falls back to LLM-only if no real file keys (Theo's data is synthetic)
5. Reports what Figma context was gathered in the execution output

**Current state:** Figma connection verified ✓, no real file keys in synthetic data → LLM-calibrated challenges

---

### 4. Upgraded NotionOrganizer (`notion_organizer.py`)

**Composio actions used:**
- `NOTION_SEARCH_NOTION_PAGE` (**READ**) — checks for existing pages before creating (avoid duplicates)
- `NOTION_CREATE_NOTION_PAGE` (**WRITE**) — creates root workspace page
- `NOTION_CREATE_DATABASE` (**WRITE**) — creates Client Pipeline, Debt Tracker databases
- `NOTION_INSERT_ROW_DATABASE` (**WRITE**) — pre-populates rows from Theo's transaction data
- `NOTION_ADD_MULTIPLE_PAGE_CONTENT` (**WRITE**) — adds markdown content blocks to pages

**New behavior:**
1. Searches for existing "Questline" page before creating (idempotent)
2. Creates root page → databases as children → inserts rows from extracted transactions
3. LLM receives Theo's recent income records to generate realistic initial rows

**Current blocker:** Root page creation fails — `NOTION_CREATE_NOTION_PAGE` requires a valid `parent_id` (UUID of an existing page), but we don't have one. The workspace ID (`cc7dc7fb...`) and user ID (`1689599c...`) both return 404. Need to either:
- `NOTION_SEARCH_NOTION_PAGE` with empty query to find any existing root page
- Or check if the Notion bot has been given access to any specific pages

**Test result:** Search works ✓, page creation blocked by missing parent_id ✗

---

### 5. Upgraded ContentCreator (`content_creator.py`)

**Composio actions used:**
- `FACEBOOK_GET_PAGE_POSTS` (**READ**) — fetches recent posts for voice calibration
- `FACEBOOK_CREATE_POST` (**WRITE**) — creates posts with `published: false + scheduled_publish_time`

**New behavior:**
1. Fetches recent Facebook posts before planning (0 returned — likely needs a FB Page not Profile)
2. LLM generates posts with unix timestamps for scheduling
3. Posts are created as scheduled drafts (not published immediately)

**Test result:** 1 post created/scheduled ✓

---

### 6. Fixed OutcomeCollector (`outcome_collector.py`)

Corrected action names:
- `NOTION_SEARCH` → `NOTION_SEARCH_NOTION_PAGE`
- Added `params=` and `app_name=` kwargs to match new `execute_action` signature

---

### 7. E2E Test Suite (`tests/test_e2e_composio.py`)

A full pytest suite organized in 5 layers:

| Class | What it tests | Speed |
|-------|--------------|-------|
| `TestConnectivity` | 4 connections exist | <1s |
| `TestComposioRawActions` | Read-only actions, all 4 apps | ~7s |
| `TestCalendarCoach` | FreeBusy → plan → create → verify | ~3min |
| `TestFigmaLearning` | GET_CURRENT_USER → calibrated challenges | ~3min |
| `TestNotionOrganizer` | Search → create page → DB → rows | ~3min |
| `TestContentCreator` | GET_PAGE_POSTS → create scheduled posts | ~3min |
| `TestFullPipeline` | Full QuestOrchestrator with all agents | ~5min |
| `TestOutcomeCollector` | Verify created items via read calls | ~5min |

**Run fast (read-only):**
```bash
uv run pytest tests/test_e2e_composio.py::TestConnectivity tests/test_e2e_composio.py::TestComposioRawActions -v -s
```

**Run all:**
```bash
uv run pytest tests/test_e2e_composio.py -v -s
```

---

## Current Test Results

| Test | Status | Notes |
|------|--------|-------|
| Connectivity (4 apps) | ✓ All pass | |
| GCal FREE_BUSY_QUERY | ✓ | Returns 7 busy slots/week |
| GCal FIND_EVENT | ✓ | |
| Notion SEARCH_NOTION_PAGE | ✓ | |
| Figma GET_CURRENT_USER | ✓ | Saksham Adhikari |
| Facebook GET_PAGE_POSTS | ✓ | Returns empty (no FB Page yet) |
| CalendarCoach plan + execute | ✓ | 12/12 events created |
| CalendarCoach verify | ✓ | FIND_EVENT confirms creation |
| FigmaLearning plan + execute | ✓ | Figma verified, 3 challenges generated |
| NotionOrganizer plan + execute | ✗ | Root page creation fails (no parent_id) |
| NotionOrganizer DB + rows | ✗ | Blocked by same issue |
| ContentCreator plan + execute | ✓ | 1 post scheduled |
| Full pipeline (orchestrator) | ✓ | ≥2 agents succeed |
| OutcomeCollector | ✓ | |

**Score: 12/14 passing**

---

## What's Left

### Blocker: Notion parent_id

The Notion bot needs a valid page UUID to create pages under. Fix options (pick one):

**Option A** — Search for any existing page and use it as root:
```python
result = await execute_action("NOTION_SEARCH_NOTION_PAGE", params={"search_term": ""})
# Use first result's id as parent
```

**Option B** — Pre-configure a known workspace page ID (e.g. a "Questline" sandbox page created manually once, stored in `.env` as `NOTION_ROOT_PAGE_ID`).

**Option C** — Use the Notion API's workspace parent directly (may require Composio support for the `workspace: true` parent type).

### Remaining agent upgrades (from plan)

| Agent | Action | Status |
|-------|--------|--------|
| CalendarCoach | `GOOGLECALENDAR_DUPLICATE_CALENDAR` — create dedicated "Questline" calendar | Not started |
| NotionOrganizer | `NOTION_QUERY_DATABASE` — verify rows were inserted (outcome) | Not started |
| ContentCreator | `FACEBOOK_GET_POST` — verify post metrics after creation | Not started |
| FigmaLearning | `FIGMA_EXTRACT_DESIGN_TOKENS` — activate when real file_key available | Blocked by synthetic data |
| FigmaLearning | `FIGMA_DOWNLOAD_FIGMA_IMAGES` → feed screenshots to ContentCreator | Not started |

### Cross-agent pipeline (stretch)

The FigmaLearning → ContentCreator handoff (portfolio screenshots → photo posts) is designed but not wired up yet. Needs:
1. FigmaLearning to store downloaded image URLs in the plan output
2. ContentCreator to use those URLs in `FACEBOOK_CREATE_PHOTO_POST`

---

## Implementation Cycle Position

```
[✓] Composio SDK fixed       — correct API, all 4 connections working
[✓] CalendarCoach upgraded   — FreeBusy → Create → Verify, full Composio loop
[✓] FigmaLearning upgraded   — connection verified, real context surfaced to LLM
[~] NotionOrganizer upgraded  — search + DB schema working, root page creation blocked
[✓] ContentCreator upgraded  — reads posts, schedules drafts
[✓] E2E test suite           — 12/14 passing, layered fast→slow
[ ] Cross-agent data flow    — FigmaLearning screenshots → ContentCreator posts
[ ] Outcome verification     — NOTION_QUERY_DATABASE, FACEBOOK_GET_POST
[ ] API endpoint test        — /api/quest curl test not run yet
```

The core integration is working end-to-end. The Notion parent_id issue is the only real blocker remaining, and it has a clear fix path.
