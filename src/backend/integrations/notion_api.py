"""Notion API integration using official notion-client SDK."""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ENV_PATH = "/home/sadhikari/.openclaw/workspace-rewind-cleanup/porthon/.env"


def _get_api_key():
    """Lazy load API key."""
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH)
    return os.environ.get("NOTION_INTEGRATION_SECRET")


class NotionAPI:
    """Official Notion SDK client."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or _get_api_key()
        if not self.api_key:
            raise ValueError("NOTION_INTEGRATION_SECRET not found")
        
        from notion_client import Client
        self.client = Client(auth=self.api_key)
        self._parent_page_id = None
    
    def _get_parent_page_id(self) -> str:
        """Find a valid parent page."""
        if self._parent_page_id:
            return self._parent_page_id
        
        # Search for Questline page
        results = self.client.search(query="Questline", page_size=5)
        pages = [r for r in results.get('results', []) if r.get('object') == 'page']
        
        if pages:
            self._parent_page_id = pages[0].get('id')
            return self._parent_page_id
        
        # Use any available page
        results = self.client.search(query="", page_size=1)
        if results.get('results'):
            self._parent_page_id = results['results'][0]['get']('id')
            return self._parent_page_id
        
        raise ValueError("No accessible pages found in Notion")
    
    def create_database(self, parent_page_id: str = None, title: str, properties: dict) -> dict:
        """Create a database in a Notion page."""
        parent_id = parent_page_id or self._get_parent_page_id()
        
        db = {
            "parent": {"page_id": parent_id},
            "title": [{"text": {"content": title}}],
            "properties": properties
        }
        
        result = self.client.databases.create(**db)
        return result
    
    def create_page(self, parent_id: str = None, title: str = "Untitled", content: list = None) -> dict:
        """Create a page in Notion."""
        parent = parent_id or self._get_parent_page_id()
        
        props = {
            "title": {
                "title": [{"text": {"content": title}}]
            }
        }
        
        children = []
        if content:
            for block_text in content:
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": block_text}}]
                    }
                })
        
        page = {
            "parent": {"page_id": parent},
            "properties": props,
        }
        if children:
            page["children"] = children
        
        result = self.client.pages.create(**page)
        return result
    
    def add_page_to_database(self, database_id: str, properties: dict) -> dict:
        """Add a page (row) to a database."""
        props = {}
        for key, value in properties.items():
            if isinstance(value, str):
                props[key] = {"rich_text": [{"text": {"content": value}}]}
            elif isinstance(value, bool):
                props[key] = {"checkbox": value}
            elif isinstance(value, int):
                props[key] = {"number": value}
        
        page = {
            "parent": {"database_id": database_id},
            "properties": props
        }
        
        result = self.client.pages.create(**page)
        return result
    
    def query_database(self, database_id: str, filter: dict = None) -> dict:
        """Query a database."""
        kwargs = {"database_id": database_id}
        if filter:
            kwargs["filter"] = filter
        
        result = self.client.databases.query(**kwargs)
        return result
    
    def get_page(self, page_id: str) -> dict:
        """Get a page."""
        result = self.client.pages.retrieve(page_id=page_id)
        return result
    
    def create_scenario_page(self, scenario_title: str, goals: list, challenges: list) -> dict:
        """Create a full scenario page with goals and challenges."""
        parent = self._get_parent_page_id()
        
        # Build blocks
        children = [
            {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"text": {"content": "🎯 Goals"}}]}}
        ]
        
        for goal in goals:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": f"• {goal}"}}]}
            })
        
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "📅 Weekly Challenges"}}]}
        })
        
        for challenge in challenges:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": f"• {challenge}"}}]}
            })
        
        page = {
            "parent": {"page_id": parent},
            "properties": {
                "title": {"title": [{"text": {"content": scenario_title}}]}
            },
            "children": children
        }
        
        result = self.client.pages.create(**page)
        return result


def get_notion_api() -> NotionAPI:
    return NotionAPI()
