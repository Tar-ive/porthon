"""Notion Opportunity Tracker Worker — quest progress + workspace pages.

Absorbs the quest tracking portion of agents/notion_organizer.py:
  - Root workspace page creation
  - Quest progress tracking pages
  - Content block addition

Composio actions:
  NOTION_CREATE_NOTION_PAGE          — create pages
  NOTION_ADD_MULTIPLE_PAGE_CONTENT   — add content blocks
  NOTION_SEARCH_NOTION_PAGE          — avoid duplicates
"""

from __future__ import annotations

import logging
import os

from deepagent.workers.base import BaseWorker, WorkerExecution
from integrations.composio_client import execute_action

logger = logging.getLogger(__name__)


class NotionOpportunityWorker(BaseWorker):
    worker_id = "notion_opportunity_worker"
    label = "Notion Opportunity Tracker"

    ACTIONS = {
        "create_workspace": "_create_workspace",
        "add_progress_page": "_add_progress_page",
        "sync_opportunities": "_create_workspace",
        "create_opportunity": "_create_workspace",
    }

    async def execute(self, action: str, payload: dict) -> WorkerExecution:
        handler_name = self.ACTIONS.get(action)
        if not handler_name:
            return WorkerExecution(ok=False, message=f"Unknown action: {action}")
        handler = getattr(self, handler_name)
        return await handler(payload)

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

    async def _create_workspace(self, payload: dict) -> WorkerExecution:
        """Create (or reuse) the root Questline workspace page."""
        if payload.get("demo_mode") or os.environ.get("PORTTHON_OFFLINE_MODE") == "1":
            scenario_title = payload.get("scenario_title", "Questline")
            root_title = f"Questline: {scenario_title}"
            return WorkerExecution(
                ok=True,
                message=f"Created workspace: {root_title} (demo)",
                data={
                    "page_id": "demo_notion_workspace",
                    "reused": False,
                    "workspace_title": root_title,
                    "progress_page": "Progress: Next Actions",
                },
            )

        kg_context = payload.get("kg_context", {})
        scenario_title = payload.get("scenario_title", "Questline")
        root_title = f"Questline: {scenario_title}"

        # Check for existing workspace
        existing = await self._find_existing_page(root_title)
        if existing:
            logger.info("Notion Opportunity: reusing workspace %s", existing)
            return WorkerExecution(
                ok=True,
                message=f"Workspace '{root_title}' already exists",
                data={"page_id": existing, "reused": True},
            )

        parent_id = payload.get("parent_id") or os.environ.get("NOTION_ROOT_PAGE_ID")
        if not parent_id:
            # Discover a parent
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
            return WorkerExecution(ok=False, message="No parent page found for workspace")

        result = await execute_action(
            "NOTION_CREATE_NOTION_PAGE",
            params={
                "parent_id": parent_id,
                "title": root_title,
                "icon": "🗺️",
            },
            app_name="notion",
        )

        if result.get("dry_run") or result.get("error"):
            return WorkerExecution(
                ok=False,
                message=f"Failed to create workspace: {result.get('error', 'dry run')}",
                data=result,
            )

        page_id = result.get("result", {}).get("data", {}).get("id")
        logger.info("Notion Opportunity: created workspace %s", page_id)

        return WorkerExecution(
            ok=True,
            message=f"Created workspace: {root_title}",
            data={"page_id": page_id, "reused": False},
        )

    async def _add_progress_page(self, payload: dict) -> WorkerExecution:
        """Add a progress update page under the workspace."""
        parent_id = payload.get("workspace_id", "")
        if not parent_id:
            return WorkerExecution(ok=False, message="workspace_id required")

        title = payload.get("title", "Progress Update")
        content = payload.get("content_markdown", "")

        # Create the page
        page_result = await execute_action(
            "NOTION_CREATE_NOTION_PAGE",
            params={"parent_id": parent_id, "title": title},
            app_name="notion",
        )

        if page_result.get("dry_run") or page_result.get("error"):
            return WorkerExecution(
                ok=False,
                message=f"Failed to create progress page: {page_result.get('error', 'dry run')}",
            )

        page_id = page_result.get("result", {}).get("data", {}).get("id")

        # Add content blocks if provided
        if content and page_id:
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()][:5]
            blocks = [{"type": "paragraph", "text": p} for p in paragraphs]
            await execute_action(
                "NOTION_ADD_MULTIPLE_PAGE_CONTENT",
                params={"parent_block_id": page_id, "content_blocks": blocks},
                app_name="notion",
            )

        return WorkerExecution(
            ok=True,
            message=f"Added progress page: {title}",
            data={"page_id": page_id},
        )
