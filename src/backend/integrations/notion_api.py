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
        
        from notion import Notion
        self.client = Notion(auth=self.api_key)
    
    def create_database(self, parent_page_id: str, title: str, properties: dict) -> dict:
        """Create a database in a Notion page."""
        from notion.models import CreateDatabase
        
        # Build title
        title_prop = [{"text": {"content": title}}]
        
        db = CreateDatabase(
            parent={"page_id": parent_page_id},
            title=title_prop,
            properties=properties
        )
        
        result = self.client.databases.create(database=db)
        return result.raw
    
    def create_page(self, parent_id: str, title: str, content: list = None) -> dict:
        """Create a page in Notion."""
        from notion.models import CreatePage
        
        # Build title property
        props = {
            "title": {
                "title": [{"text": {"content": title}}]
            }
        }
        
        # Build children blocks
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
        
        page = CreatePage(
            parent={"page_id": parent_id},
            properties=props,
            children=children if children else None
        )
        
        result = self.client.pages.create(page=page)
        return result.raw
    
    def add_page_to_database(self, database_id: str, properties: dict) -> dict:
        """Add a page (row) to a database."""
        from notion.models import CreatePage
        
        # Build properties
        props = {}
        for key, value in properties.items():
            if isinstance(value, str):
                props[key] = {"rich_text": [{"text": {"content": value}}]}
            elif isinstance(value, bool):
                props[key] = {"checkbox": value}
            elif isinstance(value, int):
                props[key] = {"number": value}
        
        page = CreatePage(
            parent={"database_id": database_id},
            properties=props
        )
        
        result = self.client.pages.create(page=page)
        return result.raw
    
    def query_database(self, database_id: str, filter: dict = None) -> dict:
        """Query a database."""
        result = self.client.databases.query(
            database_id=database_id,
            filter=filter
        )
        return result.raw
    
    def get_page(self, page_id: str) -> dict:
        """Get a page."""
        result = self.client.pages.retrieve(page_id=page_id)
        return result.raw


def get_notion_api() -> NotionAPI:
    return NotionAPI()
