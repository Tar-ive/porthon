"""Notion Leads Tracker Worker — client pipeline management.

Absorbs the client pipeline portion of agents/notion_organizer.py:
  - Database creation for client tracking
  - Row insertion with extracted transaction data
  - Duplicate detection via search

Composio actions:
  NOTION_SEARCH_NOTION_PAGE   — find existing pages
  NOTION_CREATE_DATABASE      — create client pipeline DB
  NOTION_INSERT_ROW_DATABASE  — add client rows
"""

from __future__ import annotations

import logging
import os

from deepagent.workers.base import BaseWorker, WorkerExecution
from integrations.composio_client import execute_action

logger = logging.getLogger(__name__)


class NotionLeadsWorker(BaseWorker):
    worker_id = "notion_leads_worker"
    label = "Notion Leads Tracker"

    ACTIONS = {
        "create_pipeline": "_create_pipeline",
        "add_lead": "_add_lead",
        "search_leads": "_search_leads",
        "sync_leads": "_create_pipeline",
        "create_lead": "_add_lead",
    }

    async def execute(self, action: str, payload: dict) -> WorkerExecution:
        handler_name = self.ACTIONS.get(action)
        if not handler_name:
            return WorkerExecution(ok=False, message=f"Unknown action: {action}")
        handler = getattr(self, handler_name)
        return await handler(payload)

    def _default_db_properties(self) -> list[dict]:
        return [
            {"name": "Name", "type": "title"},
            {"name": "Status", "type": "select", "options": ["Lead", "Proposal", "Active", "Completed"]},
            {"name": "Value", "type": "number"},
            {"name": "Source", "type": "select", "options": ["Referral", "Direct", "Portfolio", "Social"]},
        ]

    async def _find_existing_page(self, title: str) -> str | None:
        """Search for an existing page to avoid duplicates."""
        result = await execute_action(
            "NOTION_SEARCH_NOTION_PAGE",
            params={"search_term": title},
            app_name="notion",
        )
        if result.get("dry_run"):
            return None
        results = result.get("result", {}).get("data", {}).get("results", [])
        for r in results:
            props = r.get("properties", {})
            for prop in props.values():
                if prop.get("type") == "title":
                    texts = prop.get("title", [])
                    if texts and title.lower() in (texts[0].get("plain_text", "")).lower():
                        return r.get("id")
        return None

    async def _create_pipeline(self, payload: dict) -> WorkerExecution:
        """Create a client pipeline database in Notion."""
        if payload.get("demo_mode") or os.environ.get("PORTTHON_OFFLINE_MODE") == "1":
            return WorkerExecution(
                ok=True,
                message="Client pipeline database created (demo)",
                data={
                    "database_id": "demo_notion_pipeline",
                    "reused": False,
                    "title": "Client Pipeline",
                    "leads": [
                        {"name": "Referral Lead", "source": "Referral", "status": "Lead"},
                        {"name": "Portfolio Lead", "source": "Portfolio", "status": "Proposal"},
                        {"name": "Direct Lead", "source": "Direct", "status": "Lead"},
                    ],
                },
            )

        kg_context = payload.get("kg_context", {})
        parent_id = payload.get("parent_id") or os.environ.get("NOTION_ROOT_PAGE_ID")

        if not parent_id:
            # Try to discover a parent page
            result = await execute_action(
                "NOTION_SEARCH_NOTION_PAGE",
                params={"search_term": ""},
                app_name="notion",
            )
            if not result.get("dry_run"):
                pages = result.get("result", {}).get("data", {}).get("results", [])
                if pages:
                    parent_id = pages[0].get("id")

        if not parent_id:
            return WorkerExecution(ok=False, message="No parent page found for pipeline DB")

        # Check for existing pipeline
        existing = await self._find_existing_page("Client Pipeline")
        if existing:
            logger.info("Notion Leads: reusing existing pipeline DB %s", existing)
            return WorkerExecution(
                ok=True,
                message="Client pipeline already exists",
                data={"database_id": existing, "reused": True},
            )

        # Create the database
        result = await execute_action(
            "NOTION_CREATE_DATABASE",
            params={
                "parent_id": parent_id,
                "title": "Client Pipeline",
                "properties": self._default_db_properties(),
            },
            app_name="notion",
        )

        if result.get("dry_run") or result.get("error"):
            return WorkerExecution(
                ok=False,
                message=f"Failed to create pipeline: {result.get('error', 'dry run')}",
                data=result,
            )

        db_id = result.get("result", {}).get("data", {}).get("id")
        logger.info("Notion Leads: created pipeline DB %s", db_id)

        return WorkerExecution(
            ok=True,
            message="Client pipeline database created",
            data={"database_id": db_id, "reused": False},
        )

    async def _add_lead(self, payload: dict) -> WorkerExecution:
        """Add a lead to the pipeline database."""
        database_id = payload.get("database_id", "")
        if not database_id:
            return WorkerExecution(ok=False, message="database_id required")

        props = [
            {"name": "Name", "value": payload.get("name", "New Lead")},
            {"name": "Status", "value": payload.get("status", "Lead")},
            {"name": "Value", "value": payload.get("value", 0)},
        ]

        result = await execute_action(
            "NOTION_INSERT_ROW_DATABASE",
            params={"database_id": database_id, "properties": props},
            app_name="notion",
        )

        return WorkerExecution(
            ok=not result.get("dry_run", True),
            message=f"Added lead: {payload.get('name', 'New Lead')}",
            data=result,
        )

    async def _search_leads(self, payload: dict) -> WorkerExecution:
        """Search existing leads in Notion."""
        search_term = payload.get("search_term", "")
        result = await execute_action(
            "NOTION_SEARCH_NOTION_PAGE",
            params={"search_term": search_term},
            app_name="notion",
        )
        pages = result.get("result", {}).get("data", {}).get("results", []) if not result.get("dry_run") else []
        return WorkerExecution(
            ok=True,
            message=f"Found {len(pages)} results",
            data={"results": pages[:10]},
        )
