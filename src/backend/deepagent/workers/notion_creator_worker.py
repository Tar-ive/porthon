"""Notion Creator Worker - Creates Notion databases, pages, and leads.

Uses the official Notion SDK to create:
- Client Pipeline databases
- Opportunity workspaces
- Task trackers
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from deepagent.workers.base import BaseWorker, WorkerExecution

logger = logging.getLogger(__name__)

# Import Notion SDK
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

# Lazy load to handle missing env
_notion_api = None

def _get_notion():
    global _notion_api
    if _notion_api is None:
        from integrations.notion_api import NotionAPI
        _notion_api = NotionAPI()
    return _notion_api


class NotionCreatorWorker(BaseWorker):
    worker_id = "notion_creator_worker"
    label = "Notion Creator"

    ACTIONS = {
        "create_leads_database": "_create_leads_database",
        "create_opportunity_workspace": "_create_opportunity_workspace",
        "add_lead": "_add_lead",
        "add_opportunity": "_add_opportunity",
        "query_leads": "_query_leads",
        "create_tracker": "_create_tracker",
    }

    async def execute(self, action: str, payload: dict) -> WorkerExecution:
        handler_name = self.ACTIONS.get(action)
        if not handler_name:
            return WorkerExecution(ok=False, message=f"Unknown action: {action}")
        handler = getattr(self, handler_name)
        return await handler(payload)

    async def _create_leads_database(self, payload: dict) -> WorkerExecution:
        """Create a client pipeline database in Notion."""
        parent_page_id = payload.get("parent_page_id", os.environ.get("NOTION_PARENT_PAGE_ID"))
        
        if not parent_page_id:
            return WorkerExecution(
                ok=False,
                message="No parent_page_id provided. Set NOTION_PARENT_PAGE_ID in .env"
            )
        
        try:
            notion = _get_notion()
            
            # Define leads database properties
            properties = {
                "Name": {"title": {}},
                "Source": {
                    "select": {
                        "options": [
                            {"name": "Referral", "color": "green"},
                            {"name": "Portfolio", "color": "blue"},
                            {"name": "Direct", "color": "purple"},
                            {"name": "Social", "color": "yellow"},
                        ]
                    }
                },
                "Status": {
                    "select": {
                        "options": [
                            {"name": "Lead", "color": "gray"},
                            {"name": "Proposal", "color": "yellow"},
                            {"name": "Negotiation", "color": "orange"},
                            {"name": "Won", "color": "green"},
                            {"name": "Lost", "color": "red"},
                        ]
                    }
                },
                "Value": {"number": {}},
                "Contact": {"rich_text": {}},
                "Notes": {"rich_text": {}},
            }
            
            result = await notion.create_database(
                parent_page_id=parent_page_id,
                title="Client Pipeline",
                properties=properties
            )
            
            return WorkerExecution(
                ok=True,
                message="Created Client Pipeline database!",
                data={
                    "database_id": result.get("id"),
                    "url": f"https://notion.so/{result.get('id').replace('-', '')}"
                }
            )
            
        except Exception as e:
            logger.error(f"Notion error: {e}")
            return WorkerExecution(ok=False, message=str(e))

    async def _create_opportunity_workspace(self, payload: dict) -> WorkerExecution:
        """Create an opportunity tracking workspace."""
        parent_page_id = payload.get("parent_page_id", os.environ.get("NOTION_PARENT_PAGE_ID"))
        
        if not parent_page_id:
            return WorkerExecution(
                ok=False,
                message="No parent_page_id provided"
            )
        
        try:
            notion = _get_notion()
            
            # Create workspace page
            workspace_title = payload.get("workspace_title", "Questline: Opportunity Tracker")
            
            result = await notion.create_page(
                parent_id=parent_page_id,
                title=workspace_title,
                content=[
                    "🎯 This workspace tracks opportunities for your scenario.",
                    "Add your progress notes below.",
                ]
            )
            
            return WorkerExecution(
                ok=True,
                message=f"Created workspace: {workspace_title}",
                data={
                    "page_id": result.get("id"),
                    "url": f"https://notion.so/{result.get('id').replace('-', '')}"
                }
            )
            
        except Exception as e:
            return WorkerExecution(ok=False, message=str(e))

    async def _add_lead(self, payload: dict) -> WorkerExecution:
        """Add a lead to the database."""
        database_id = payload.get("database_id", os.environ.get("NOTION_LEADS_DB_ID"))
        
        if not database_id:
            return WorkerExecution(
                ok=False,
                message="No database_id provided. Set NOTION_LEADS_DB_ID in .env"
            )
        
        try:
            notion = _get_notion()
            
            properties = {
                "Name": payload.get("name", "Unnamed Lead"),
                "Source": payload.get("source", "Direct"),
                "Status": payload.get("status", "Lead"),
                "Value": payload.get("value", 0),
                "Contact": payload.get("contact", ""),
                "Notes": payload.get("notes", ""),
            }
            
            result = await notion.add_page_to_database(database_id, properties)
            
            return WorkerExecution(
                ok=True,
                message=f"Added lead: {properties['Name']}",
                data={
                    "page_id": result.get("id"),
                }
            )
            
        except Exception as e:
            return WorkerExecution(ok=False, message=str(e))

    async def _add_opportunity(self, payload: dict) -> WorkerExecution:
        """Add an opportunity to tracking."""
        database_id = payload.get("database_id", os.environ.get("NOTION_OPPORTUNITIES_DB_ID"))
        
        try:
            notion = _get_notion()
            
            properties = {
                "Name": payload.get("name", "Unnamed Opportunity"),
                "Stage": payload.get("stage", "Discovery"),
                "Value": payload.get("value", 0),
                "Close Date": payload.get("close_date", ""),
                "Notes": payload.get("notes", ""),
            }
            
            result = await notion.add_page_to_database(database_id, properties)
            
            return WorkerExecution(
                ok=True,
                message=f"Added opportunity: {properties['Name']}",
                data={"page_id": result.get("id")}
            )
            
        except Exception as e:
            return WorkerExecution(ok=False, message=str(e))

    async def _query_leads(self, payload: dict) -> WorkerExecution:
        """Query leads from database."""
        database_id = payload.get("database_id", os.environ.get("NOTION_LEADS_DB_ID"))
        
        if not database_id:
            return WorkerExecution(ok=False, message="No database_id")
        
        try:
            notion = _get_notion()
            result = await notion.query_database(database_id)
            
            leads = []
            for page in result.get("results", []):
                props = page.get("properties", {})
                leads.append({
                    "id": page.get("id"),
                    "name": props.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Unknown"),
                    "status": props.get("Status", {}).get("select", {}).get("name", "Unknown"),
                })
            
            return WorkerExecution(
                ok=True,
                message=f"Found {len(leads)} leads",
                data={"leads": leads}
            )
            
        except Exception as e:
            return WorkerExecution(ok=False, message=str(e))

    async def _create_tracker(self, payload: dict) -> WorkerExecution:
        """Create a general task tracker."""
        parent_page_id = payload.get("parent_page_id", os.environ.get("NOTION_PARENT_PAGE_ID"))
        
        try:
            notion = _get_notion()
            
            tracker_title = payload.get("title", "Questline Task Tracker")
            
            result = await notion.create_page(
                parent_id=parent_page_id,
                title=tracker_title,
                content=[
                    "📋 Task Tracker",
                    "Use this page to track tasks for your current scenario.",
                    "",
                    "## Tasks",
                    "- [ ] Task 1",
                    "- [ ] Task 2",
                ]
            )
            
            return WorkerExecution(
                ok=True,
                message=f"Created tracker: {tracker_title}",
                data={"page_id": result.get("id")}
            )
            
        except Exception as e:
            return WorkerExecution(ok=False, message=str(e))
