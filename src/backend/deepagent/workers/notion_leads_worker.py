"""Notion Leads Tracker Worker — deterministic Notion CRM operations."""

from __future__ import annotations

import logging
import os
from typing import Any

from deepagent.workers.base import BaseWorker, WorkerExecution
from integrations.notion_leads_service import (
    default_demo_leads,
    get_notion_leads_service,
)

logger = logging.getLogger(__name__)


class NotionLeadsWorker(BaseWorker):
    worker_id = "notion_leads_worker"
    label = "Notion Leads Tracker"

    ACTIONS = {
        "ensure_pipeline": "_ensure_pipeline",
        "create_pipeline": "_ensure_pipeline",  # backward compatibility
        "sync_leads": "_sync_leads",
        "add_lead": "_upsert_lead",  # backward compatibility
        "create_lead": "_upsert_lead",  # backward compatibility
        "upsert_lead": "_upsert_lead",
        "patch_lead": "_patch_lead",
        "list_leads": "_list_leads",
        "search_leads": "_list_leads",  # backward compatibility
    }

    async def execute(self, action: str, payload: dict) -> WorkerExecution:
        handler_name = self.ACTIONS.get(action)
        if not handler_name:
            return WorkerExecution(ok=False, message=f"Unknown action: {action}")
        handler = getattr(self, handler_name)
        return await handler(payload)

    def _is_demo(self, payload: dict[str, Any]) -> bool:
        return bool(payload.get("demo_mode")) or os.environ.get("PORTTHON_OFFLINE_MODE") == "1"

    def _default_parent_page_id(self, payload: dict[str, Any]) -> str:
        return str(
            payload.get("parent_page_id")
            or payload.get("parent_id")
            or os.environ.get("NOTION_ROOT_PAGE_ID")
            or os.environ.get("NOTION_PARENT_PAGE_ID")
            or ""
        ).strip()

    async def _ensure_workspace(self, payload: dict[str, Any]) -> dict[str, Any]:
        service = get_notion_leads_service()
        if not service.is_configured():
            raise ValueError("NOTION_INTEGRATION_SECRET is not configured")
        return await service.ensure_workspace(
            parent_page_id=self._default_parent_page_id(payload) or None,
            database_title=str(payload.get("database_title") or "Leads"),
            data_source_title=str(payload.get("data_source_title") or "Theo Leads"),
            database_id=str(payload.get("database_id", "")).strip() or None,
            data_source_id=str(payload.get("data_source_id", "")).strip() or None,
        )

    async def _ensure_pipeline(self, payload: dict) -> WorkerExecution:
        """Ensure deterministic leads database + data source exist and schema is enforced."""
        if payload.get("demo_mode") or os.environ.get("PORTTHON_OFFLINE_MODE") == "1":
            return WorkerExecution(
                ok=True,
                message="Leads database ready (demo)",
                data={
                    "database_id": "demo_notion_pipeline",
                    "data_source_id": "demo_notion_leads",
                    "database_title": "Leads",
                    "data_source_title": "Theo Leads",
                    "reused": True,
                    "leads": default_demo_leads(),
                    "external_links": {
                        "notion_database": "https://www.notion.so/demo_notion_pipeline"
                    },
                },
            )

        try:
            setup = await self._ensure_workspace(payload)
            return WorkerExecution(
                ok=True,
                message="Leads database ready",
                data={
                    **setup,
                    "external_links": {"notion_database": setup.get("database_url", "")},
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Notion leads ensure pipeline failed: %s", exc)
            return WorkerExecution(ok=False, message=str(exc))

    async def _sync_leads(self, payload: dict) -> WorkerExecution:
        if self._is_demo(payload):
            leads = payload.get("leads") or default_demo_leads()
            return WorkerExecution(
                ok=True,
                message="Leads synced (demo)",
                data={
                    "database_id": "demo_notion_pipeline",
                    "data_source_id": "demo_notion_leads",
                    "counts": {
                        "desired": len(leads),
                        "created": 0,
                        "updated": 0,
                        "noop": len(leads),
                        "archived": 0,
                    },
                    "leads": leads,
                    "external_links": {
                        "notion_database": "https://www.notion.so/demo_notion_pipeline"
                    },
                },
            )

        try:
            service = get_notion_leads_service()
            setup = await self._ensure_workspace(payload)
            leads = payload.get("leads") or []
            strict_reconcile = bool(payload.get("strict_reconcile", True))
            sync = await service.sync_leads(
                data_source_id=str(setup["data_source_id"]),
                leads=leads if isinstance(leads, list) else [],
                strict_reconcile=strict_reconcile,
            )
            return WorkerExecution(
                ok=True,
                message="Leads synced",
                data={
                    **setup,
                    **sync,
                    "external_links": {"notion_database": setup.get("database_url", "")},
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Notion leads sync failed: %s", exc)
            return WorkerExecution(ok=False, message=str(exc))

    async def _upsert_lead(self, payload: dict) -> WorkerExecution:
        lead = {
            "name": payload.get("name", "New Lead"),
            "status": payload.get("status", "Lead"),
            "lead_type": payload.get("lead_type", payload.get("source", "Inbound")),
            "priority": payload.get("priority", "Medium"),
            "deal_size": payload.get("deal_size", payload.get("value", 0)),
            "last_contact": payload.get("last_contact"),
            "next_action": payload.get("next_action", ""),
            "next_follow_up_date": payload.get("next_follow_up_date"),
            "email_handle": payload.get("email_handle", ""),
            "source": payload.get("source", "Unknown"),
            "notes": payload.get("notes", ""),
            "lead_key": payload.get("lead_key", ""),
        }
        merged_payload = dict(payload)
        merged_payload["leads"] = [lead]
        merged_payload["strict_reconcile"] = False
        result = await self._sync_leads(merged_payload)
        if not result.ok:
            return result
        return WorkerExecution(
            ok=True,
            message=f"Upserted lead: {lead['name']}",
            data=result.data,
        )

    async def _patch_lead(self, payload: dict) -> WorkerExecution:
        if self._is_demo(payload):
            lead_key = str(payload.get("lead_key", "demo::lead")).strip()
            return WorkerExecution(
                ok=True,
                message="Lead patched (demo)",
                data={
                    "lead_key": lead_key,
                    "external_links": {
                        "notion_database": "https://www.notion.so/demo_notion_pipeline"
                    },
                },
            )

        lead_key = str(payload.get("lead_key", "")).strip()
        if not lead_key:
            name = str(payload.get("name", "")).strip()
            source = str(payload.get("source", "")).strip()
            if name and source:
                lead_key = f"{name.lower()}::{source.lower()}"
        if not lead_key:
            return WorkerExecution(ok=False, message="lead_key required")

        try:
            service = get_notion_leads_service()
            setup = await self._ensure_workspace(payload)
            patch = {
                "name": payload.get("name"),
                "status": payload.get("status"),
                "lead_type": payload.get("lead_type"),
                "priority": payload.get("priority"),
                "deal_size": payload.get("deal_size", payload.get("value")),
                "last_contact": payload.get("last_contact"),
                "next_action": payload.get("next_action"),
                "next_follow_up_date": payload.get("next_follow_up_date"),
                "email_handle": payload.get("email_handle"),
                "source": payload.get("source"),
                "notes": payload.get("notes"),
            }
            patch = {k: v for k, v in patch.items() if v is not None}
            result = await service.patch_lead(
                data_source_id=str(setup["data_source_id"]),
                lead_key=lead_key,
                patch=patch,
            )
            return WorkerExecution(
                ok=True,
                message=f"Patched lead: {lead_key}",
                data={
                    **setup,
                    **result,
                    "external_links": {"notion_database": setup.get("database_url", "")},
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Notion leads patch failed: %s", exc)
            return WorkerExecution(ok=False, message=str(exc))

    async def _list_leads(self, payload: dict) -> WorkerExecution:
        if self._is_demo(payload):
            search_term = str(payload.get("search_term", "")).strip().lower()
            leads = default_demo_leads()
            if search_term:
                leads = [
                    l
                    for l in leads
                    if search_term in str(l.get("name", "")).lower()
                    or search_term in str(l.get("source", "")).lower()
                ]
            return WorkerExecution(
                ok=True,
                message=f"Found {len(leads)} leads (demo)",
                data={"leads": leads, "results": leads},
            )

        try:
            service = get_notion_leads_service()
            setup = await self._ensure_workspace(payload)
            leads = await service.list_leads(str(setup["data_source_id"]))
            search_term = str(payload.get("search_term", "")).strip().lower()
            if search_term:
                leads = [
                    l
                    for l in leads
                    if search_term in str(l.get("name", "")).lower()
                    or search_term in str(l.get("source", "")).lower()
                    or search_term in str(l.get("status", "")).lower()
                ]
            return WorkerExecution(
                ok=True,
                message=f"Found {len(leads)} leads",
                data={
                    **setup,
                    "leads": leads,
                    "results": leads,
                    "external_links": {"notion_database": setup.get("database_url", "")},
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Notion leads list failed: %s", exc)
            return WorkerExecution(ok=False, message=str(exc))
        return WorkerExecution(
            ok=True,
            message=f"Found {len(pages)} results",
            data={"results": pages[:10]},
        )
