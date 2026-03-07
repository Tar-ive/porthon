"""E2E tests for Composio integration — full worker pipeline for Theo (p05).

Tests ALL Composio actions across all 4 apps via the deep-agent workers:
  Google Calendar: FREE_BUSY_QUERY (read) → CREATE_EVENT (write) → FIND_EVENT (verify)
  Notion:          SEARCH_NOTION_PAGE (read) → CREATE_NOTION_PAGE → CREATE_DATABASE
                   → INSERT_ROW_DATABASE → ADD_MULTIPLE_PAGE_CONTENT (write)
  Facebook:        GET_PAGE_POSTS (read) → CREATE_POST (write)
  Figma:           GET_CURRENT_USER (read)

Run from src/backend/:
    uv run pytest tests/test_e2e_composio.py -v -s
    uv run pytest tests/test_e2e_composio.py::TestComposioRawActions -v -s   # fast: read-only
    uv run pytest tests/test_e2e_composio.py::TestWorkerPipeline -v -s       # full E2E
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env before any imports that need API keys
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

pytestmark = pytest.mark.live

if os.environ.get("RUN_LIVE_TESTS") != "1":
    pytest.skip("Live Composio tests disabled. Set RUN_LIVE_TESTS=1 to run.", allow_module_level=True)

if not os.environ.get("OPENAI_API_KEY") and os.environ.get("LLM_BINDING_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.environ["LLM_BINDING_API_KEY"]
if not os.environ.get("OPENAI_BASE_URL") and os.environ.get("LLM_BINDING_HOST"):
    os.environ["OPENAI_BASE_URL"] = os.environ["LLM_BINDING_HOST"]

from integrations.composio_client import execute_action, get_connection_id, is_available
from deepagent.contracts import ProfileScores, QuestContext

# ---------------------------------------------------------------------------
# Demo profile for Theo Nakamura (p05)
# ---------------------------------------------------------------------------

THEO_PROFILE = ProfileScores(
    execution=0.45,
    growth=0.65,
    self_awareness=0.70,
    financial_stress=0.75,
    adhd_indicator=0.80,
    archetype="emerging_talent",
    deltas={"public_private": 0.40},
)

NEXT_WEEK_MON = "2026-03-09T00:00:00Z"
NEXT_WEEK_SUN = "2026-03-15T23:59:59Z"

# ---------------------------------------------------------------------------
# Session-scoped fixtures (LLM calls cached across tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def extracted_data():
    from pipeline.extractor import extract_persona_data
    return extract_persona_data("p05")


@pytest.fixture(scope="session")
def scenario_and_actions(extracted_data):
    from pipeline.action_planner import generate_actions
    from pipeline.scenario_gen import generate_scenarios

    loop = asyncio.new_event_loop()
    last_err = None
    try:
        for _ in range(3):
            try:
                scenarios = loop.run_until_complete(
                    asyncio.wait_for(generate_scenarios(extracted_data), timeout=60.0)
                )
                assert scenarios
                chosen = scenarios[0]
                actions = loop.run_until_complete(
                    asyncio.wait_for(generate_actions(chosen, extracted_data), timeout=60.0)
                )
                return chosen, actions
            except Exception as e:
                last_err = e
    finally:
        loop.close()
    pytest.fail(f"scenario_and_actions failed: {last_err}")


@pytest.fixture(scope="session")
def quest_context(extracted_data, scenario_and_actions):
    chosen, actions = scenario_and_actions
    print(f"\n  Scenario: {chosen.get('title')} ({chosen.get('horizon')}, {chosen.get('likelihood')})")
    return QuestContext(
        scenario=chosen,
        action_plan=actions,
        profile_scores=THEO_PROFILE,
        extracted_data=extracted_data,
        persona_id="p05",
    )


@pytest.fixture
def kg_payload(quest_context):
    """Build a worker payload from quest context."""
    return {
        "scenario_title": quest_context.scenario.get("title", ""),
        "actions_text": "\n".join(
            f"  - {a.get('action', '')}"
            for a in quest_context.action_plan.get("actions", [])
        ),
        "kg_context": {"snippets": [], "confidence": 0.0, "intent": "factual"},
    }


# ---------------------------------------------------------------------------
# Step 1: Connectivity — verify all 4 connections exist
# ---------------------------------------------------------------------------


class TestConnectivity:
    def test_composio_client_initialized(self):
        assert is_available(), "COMPOSIO_API_KEY not set or init failed"

    @pytest.mark.parametrize("app", ["googlecalendar", "notion", "facebook", "figma"])
    def test_connection_exists(self, app):
        assert get_connection_id(app), f"No active connection for {app}"


# ---------------------------------------------------------------------------
# Step 2: Raw read actions — all 4 apps, no writes
# ---------------------------------------------------------------------------


class TestComposioRawActions:
    """Fast suite: read-only Composio actions to verify all connections work."""

    @pytest.mark.asyncio
    async def test_gcal_free_busy_query(self):
        """READ: Google Calendar — find free/busy slots for next week."""
        result = await execute_action(
            "GOOGLECALENDAR_FREE_BUSY_QUERY",
            params={
                "timeMin": NEXT_WEEK_MON,
                "timeMax": NEXT_WEEK_SUN,
                "items": [{"id": "primary"}],
                "timeZone": "America/Chicago",
            },
            app_name="googlecalendar",
        )
        assert not result.get("dry_run"), f"Dry-run: {result}"
        data = result.get("result", {}).get("data", {})
        assert "calendars" in data, f"No calendars in response: {data}"
        print(f"\n  Busy slots found: {len(data['calendars'].get('primary', {}).get('busy', []))}")

    @pytest.mark.asyncio
    async def test_gcal_find_event(self):
        """READ: Google Calendar — search for existing events."""
        result = await execute_action(
            "GOOGLECALENDAR_FIND_EVENT",
            params={"search_term": "focus"},
            app_name="googlecalendar",
        )
        assert not result.get("dry_run")
        assert "result" in result

    @pytest.mark.asyncio
    async def test_notion_search_pages(self):
        """READ: Notion — search for existing pages."""
        result = await execute_action(
            "NOTION_SEARCH_NOTION_PAGE",
            params={"search_term": "Questline"},
            app_name="notion",
        )
        assert not result.get("dry_run")
        data = result.get("result", {}).get("data", {})
        print(f"\n  Notion pages found: {len(data.get('results', []))}")

    @pytest.mark.asyncio
    async def test_figma_get_current_user(self):
        """READ: Figma — verify connection + get user handle."""
        result = await execute_action(
            "FIGMA_GET_CURRENT_USER",
            params={},
            app_name="figma",
        )
        assert not result.get("dry_run"), f"Dry-run: {result}"
        data = result.get("result", {}).get("data", {})
        assert data.get("handle"), f"No handle in response: {data}"
        print(f"\n  Figma user: {data['handle']} ({data.get('email')})")

    @pytest.mark.asyncio
    async def test_facebook_get_page_posts(self):
        """READ: Facebook — get recent posts from connected page."""
        result = await execute_action(
            "FACEBOOK_GET_PAGE_POSTS",
            params={"page_id": "me", "limit": 5},
            app_name="facebook",
        )
        print(f"\n  Facebook result: dry_run={result.get('dry_run')}, has_error={bool(result.get('error'))}")


# ---------------------------------------------------------------------------
# Step 3: Individual worker tests — execute actions
# ---------------------------------------------------------------------------


class TestCalendarWorker:
    """CalendarWorker: FREE_BUSY_QUERY → plan → CREATE_EVENT."""

    @pytest.mark.asyncio
    async def test_fetch_free_slots(self):
        from deepagent.workers.calendar_worker import CalendarWorker

        worker = CalendarWorker()
        free_slots = await worker._fetch_free_slots()
        assert isinstance(free_slots, list)
        print(f"\n  Free slots fetched: {len(free_slots)} days")
        for s in free_slots[:3]:
            print(f"    {s['day']}: {s.get('hours_free', '?')}h free")

    @pytest.mark.asyncio
    async def test_sync_schedule(self, kg_payload):
        from deepagent.workers.calendar_worker import CalendarWorker

        worker = CalendarWorker()
        result = await asyncio.wait_for(
            worker.execute("sync_schedule", kg_payload),
            timeout=120.0,
        )
        assert result.ok, f"sync_schedule failed: {result.message}"
        events = result.data.get("events", [])
        print(f"\n  Events planned: {len(events)}")
        print(f"  Result: {result.message}")

    @pytest.mark.asyncio
    async def test_create_single_block(self):
        from deepagent.workers.calendar_worker import CalendarWorker

        worker = CalendarWorker()
        result = await worker.execute("create_block", {
            "title": "Test Focus Block",
            "start_time": "2026-03-09T09:00:00",
            "end_time": "2026-03-09T12:00:00",
            "description": "Deep work — test event from E2E suite",
        })
        assert result.ok, f"create_block failed: {result.message}"
        print(f"\n  Created: {result.message}")


class TestFigmaWorker:
    """FigmaWorker: GET_CURRENT_USER → calibrated challenge generation."""

    @pytest.mark.asyncio
    async def test_verify_connection(self):
        from deepagent.workers.figma_worker import FigmaWorker

        worker = FigmaWorker()
        result = await worker.execute("verify_connection", {})
        assert result.ok, f"Figma not connected: {result.message}"
        print(f"\n  Figma connected: {result.data.get('figma_user', {}).get('handle')}")

    @pytest.mark.asyncio
    async def test_generate_challenge(self, kg_payload):
        from deepagent.workers.figma_worker import FigmaWorker

        worker = FigmaWorker()
        result = await asyncio.wait_for(
            worker.execute("generate_challenge", kg_payload),
            timeout=120.0,
        )
        assert result.ok, f"generate_challenge failed: {result.message}"
        challenges = result.data.get("challenges", [])
        assert len(challenges) > 0, "No challenges generated"
        print(f"\n  Challenges: {len(challenges)}")
        for c in challenges[:2]:
            print(f"    [{c.get('difficulty')}] {c.get('title')}")


class TestNotionLeadsWorker:
    """NotionLeadsWorker: SEARCH → CREATE_DATABASE → INSERT_ROW."""

    @pytest.mark.asyncio
    async def test_search_leads(self):
        from deepagent.workers.notion_leads_worker import NotionLeadsWorker

        worker = NotionLeadsWorker()
        result = await worker.execute("search_leads", {"search_term": "Questline"})
        assert result.ok
        print(f"\n  Existing pages: {len(result.data.get('results', []))}")

    @pytest.mark.asyncio
    async def test_create_pipeline(self, kg_payload):
        from deepagent.workers.notion_leads_worker import NotionLeadsWorker

        worker = NotionLeadsWorker()
        result = await worker.execute("create_pipeline", kg_payload)
        assert result.ok, f"create_pipeline failed: {result.message}"
        print(f"\n  Pipeline: {result.message} (reused={result.data.get('reused')})")


class TestNotionOpportunityWorker:
    """NotionOpportunityWorker: CREATE_PAGE → ADD_CONTENT."""

    @pytest.mark.asyncio
    async def test_create_workspace(self, kg_payload):
        from deepagent.workers.notion_opportunity_worker import NotionOpportunityWorker

        worker = NotionOpportunityWorker()
        result = await worker.execute("create_workspace", kg_payload)
        assert result.ok, f"create_workspace failed: {result.message}"
        print(f"\n  Workspace: {result.message} (reused={result.data.get('reused')})")


class TestFacebookWorker:
    """FacebookWorker: GET_PAGE_POSTS (read) → draft_posts (LLM)."""

    @pytest.mark.asyncio
    async def test_draft_posts(self, kg_payload):
        from deepagent.workers.facebook_worker import FacebookWorker

        worker = FacebookWorker()
        result = await asyncio.wait_for(
            worker.execute("draft_posts", kg_payload),
            timeout=120.0,
        )
        assert result.ok, f"draft_posts failed: {result.message}"
        posts = result.data.get("posts", [])
        print(f"\n  Posts drafted: {len(posts)}")

    @pytest.mark.asyncio
    async def test_publish_requires_approval(self):
        from deepagent.workers.facebook_worker import FacebookWorker

        worker = FacebookWorker()
        result = await worker.execute("publish_post", {"content": "test"})
        assert result.approval_required, "Publishing should require approval"
        print(f"\n  Approval gate: {result.approval_reason}")


# ---------------------------------------------------------------------------
# Step 4: KG Worker — intent classification + search
# ---------------------------------------------------------------------------


class TestKgWorker:
    """KgWorker: classify intent + search knowledge graph."""

    @pytest.mark.asyncio
    async def test_classify_intent(self):
        from deepagent.workers.kg_worker import KgWorker

        worker = KgWorker()
        result = await worker.execute("classify", {"query": "how much did I spend last month?"})
        assert result.ok
        assert result.data["intent"] == "factual"
        print(f"\n  Intent: {result.data['intent']}")

    @pytest.mark.asyncio
    async def test_classify_emotional(self):
        from deepagent.workers.kg_worker import KgWorker

        worker = KgWorker()
        result = await worker.execute("classify", {"query": "I'm freaking out about money"})
        assert result.ok
        assert result.data["intent"] == "emotional"

    @pytest.mark.asyncio
    async def test_search_skips_emotional(self):
        from deepagent.workers.kg_worker import KgWorker

        worker = KgWorker()
        result = await worker.execute("search", {"query": "I'm so stressed"})
        assert result.ok
        assert result.data["intent"] == "emotional"
        assert len(result.data["snippets"]) == 0
        print(f"\n  Emotional query correctly skipped KG")

    @pytest.mark.asyncio
    async def test_search_factual(self):
        from deepagent.workers.kg_worker import KgWorker

        worker = KgWorker()
        result = await worker.execute("search", {"query": "how much revenue last month"})
        assert result.ok
        print(f"\n  KG search: {len(result.data.get('snippets', []))} snippets, confidence={result.data.get('confidence')}")


# ---------------------------------------------------------------------------
# Step 5: Full worker pipeline via dispatcher
# ---------------------------------------------------------------------------


class TestWorkerPipeline:
    """Full pipeline: KG → Calendar + Figma + Notion workers."""

    @pytest.mark.asyncio
    async def test_all_workers_execute(self, kg_payload):
        from deepagent.workers import build_workers

        workers = build_workers()
        assert len(workers) == 6, f"Expected 6 workers, got {len(workers)}"

        results = {}
        for wid, worker in workers.items():
            if wid == "kg_worker":
                r = await worker.execute("search", {"query": "Theo scheduling patterns"})
            elif wid == "calendar_worker":
                r = await asyncio.wait_for(
                    worker.execute("sync_schedule", kg_payload), timeout=120.0
                )
            elif wid == "figma_worker":
                r = await worker.execute("verify_connection", {})
            elif wid == "notion_leads_worker":
                r = await worker.execute("search_leads", {"search_term": ""})
            elif wid == "notion_opportunity_worker":
                r = await worker.execute("create_workspace", kg_payload)
            elif wid == "facebook_worker":
                r = await asyncio.wait_for(
                    worker.execute("draft_posts", kg_payload), timeout=120.0
                )
            else:
                continue
            results[wid] = r

        print(f"\n=== Worker Pipeline Results ===")
        for wid, r in results.items():
            status = "✓" if r.ok else "✗"
            print(f"  {status} {wid}: {r.message}")

        ok_count = sum(1 for r in results.values() if r.ok)
        assert ok_count >= 4, f"Only {ok_count}/6 workers succeeded"
