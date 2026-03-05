"""
Notion API Integration for Questline

Uses the official notion-client SDK to create pages, hierarchies, 
and track leads/opportunities for Theo.

Setup:
1. Create a Notion integration at https://www.notion.so/my-integrations
2. Get the internal integration secret
3. Add to .env: NOTION_INTEGRATION_SECRET=secret
4. Share your Questline page with the integration

Reference: https://developers.notion.com
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ENV_PATH = "/home/sadhikari/.openclaw/workspace-rewind-cleanup/porthon/.env"


def _load_env():
    """Lazy load environment variables."""
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH)


def _get_api_key() -> str:
    """Get Notion API key."""
    _load_env()
    key = os.environ.get("NOTION_INTEGRATION_SECRET")
    if not key:
        raise ValueError("NOTION_INTEGRATION_SECRET not set in .env")
    return key


class NotionAPI:
    """Notion API client for Questline."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or _get_api_key()
        from notion_client import Client
        self.client = Client(auth=self.api_key)
        self._parent_page_id: Optional[str] = None
    
    def _find_parent_page(self) -> str:
        """Find or create Questline parent page."""
        if self._parent_page_id:
            return self._parent_page_id
        
        # Search for existing Questline page
        try:
            results = self.client.search(query="Questline", page_size=5)
            pages = [r for r in results.get('results', []) 
                    if r.get('object') == 'page']
            if pages:
                self._parent_page_id = pages[0].get('id')
                return self._parent_page_id
        except Exception as e:
            logger.warning(f"Search failed: {e}")
        
        # Use any accessible page
        try:
            results = self.client.search(query="", page_size=1)
            if results.get('results'):
                self._parent_page_id = results['results'][0].get('id')
                return self._parent_page_id
        except Exception as e:
            logger.warning(f"Fallback search failed: {e}")
        
        raise ValueError("No accessible Notion pages found")
    
    # -------------------------------------------------------------------------
    # Page Operations
    # -------------------------------------------------------------------------
    
    def create_page(self, parent_id: Optional[str] = None, 
                    title: str = "Untitled",
                    content: Optional[list] = None) -> dict:
        """Create a new page.
        
        Args:
            parent_id: Parent page ID (auto-discovers if None)
            title: Page title
            content: Optional list of content strings
        
        Returns:
            Created page dict with 'id' and 'url'
        """
        parent = parent_id or self._find_parent_page()
        
        props = {
            "title": [
                {"text": {"content": title}}
            ]
        }
        
        page = self.client.pages.create(
            parent={"page_id": parent},
            properties=props
        )
        
        # Add content blocks if provided
        if content:
            blocks = []
            for text in content:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"text": {"content": text}}]}
                })
            self.client.blocks.children.append(
                block_id=page.get('id'),
                children=blocks
            )
        
        page_id = page.get('id')
        return {
            "id": page_id,
            "url": f"https://notion.so/{page_id.replace('-', '')}"
        }
    
    def create_child_page(self, parent_id: str, title: str,
                         content: Optional[list] = None) -> dict:
        """Create a child page under a parent."""
        return self.create_page(parent_id=parent_id, title=title, content=content)
    
    # -------------------------------------------------------------------------
    # Lead/Client Pipeline Operations  
    # -------------------------------------------------------------------------
    
    def create_client_pipeline(self, title: str = "Client Pipeline") -> dict:
        """Create a client pipeline hierarchy.
        
        Creates:
        - Parent page (e.g., "Theo Client Pipeline")
        - Child pages for each lead
        
        Args:
            title: Name of the pipeline
        
        Returns:
            Dict with main page id and url
        """
        parent = self._find_parent_page()
        
        # Create main pipeline page
        main_page = self.client.pages.create(
            parent={"page_id": parent},
            properties={
                "title": [{"text": {"content": title}}]
            }
        )
        
        page_id = main_page.get('id')
        return {
            "id": page_id,
            "url": f"https://notion.so/{page_id.replace('-', '')}",
            "type": "pipeline"
        }
    
    def add_lead(self, pipeline_page_id: str, lead_name: str,
                 status: str = "Lead", value: int = 0,
                 source: str = "Direct", notes: str = "") -> dict:
        """Add a lead to a pipeline.
        
        Args:
            pipeline_page_id: Parent pipeline page
            lead_name: Name of the lead/client
            status: Lead status (Lead, Proposal, In Progress, etc.)
            value: Project value in dollars
            source: Lead source (Referral, Portfolio, Direct, Social)
            notes: Additional notes
        
        Returns:
            Created lead page dict
        """
        # Create lead page
        lead_text = f"{lead_name} ({status})"
        if value > 0:
            lead_text += f" - ${value}"
        
        page = self.client.pages.create(
            parent={"page_id": pipeline_page_id},
            properties={
                "title": [{"text": {"content": lead_text}}]
            }
        )
        
        # Add details as blocks
        details = []
        if status:
            details.append(f"Status: {status}")
        if value > 0:
            details.append(f"Value: ${value}")
        if source:
            details.append(f"Source: {source}")
        if notes:
            details.append(f"Notes: {notes}")
        
        if details:
            blocks = []
            for detail in details:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"text": {"content": detail}}]}
                })
            self.client.blocks.children.append(
                block_id=page.get('id'),
                children=blocks
            )
        
        page_id = page.get('id')
        return {
            "id": page_id,
            "url": f"https://notion.so/{page_id.replace('-', '')}"
        }
    
    # -------------------------------------------------------------------------
    # Scenario Operations
    # -------------------------------------------------------------------------
    
    def create_scenario_page(self, scenario_title: str,
                            goals: list,
                            challenges: list) -> dict:
        """Create a full scenario page with goals and challenges.
        
        Args:
            scenario_title: Title of the scenario
            goals: List of goal strings
            challenges: List of challenge strings
        
        Returns:
            Created page dict
        """
        parent = self._find_parent_page()
        
        # Build blocks
        blocks = []
        
        # Goals section
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "🎯 Goals"}}]}
        })
        for goal in goals:
            blocks.append({
                "object": "block",
                "type": "paragraph", 
                "paragraph": {"rich_text": [{"text": {"content": f"• {goal}"}}]}
            })
        
        # Challenges section
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "📅 Weekly Challenges"}}]}
        })
        for challenge in challenges:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": f"• {challenge}"}}]}
            })
        
        # Create page with blocks
        page = self.client.pages.create(
            parent={"page_id": parent},
            properties={
                "title": [{"text": {"content": scenario_title}}]
            },
            children=blocks
        )
        
        page_id = page.get('id')
        return {
            "id": page_id,
            "url": f"https://notion.so/{page_id.replace('-', '')}"
        }
    
    # -------------------------------------------------------------------------
    # Query Operations
    # -------------------------------------------------------------------------
    
    def search(self, query: str = "", page_size: int = 10) -> list:
        """Search Notion pages.
        
        Args:
            query: Search query
            page_size: Number of results
        
        Returns:
            List of page dicts
        """
        results = self.client.search(query=query, page_size=page_size)
        return results.get('results', [])


# Singleton instance
_notion_api: Optional[NotionAPI] = None


def get_notion_api() -> NotionAPI:
    """Get Notion API singleton."""
    global _notion_api
    if _notion_api is None:
        _notion_api = NotionAPI()
    return _notion_api
