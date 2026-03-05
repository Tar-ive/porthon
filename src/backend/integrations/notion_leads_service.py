"""Deterministic Notion leads database management via direct Notion REST API."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"
SCHEMA_VERSION = "crm_leads_v2"

STATUS_OPTIONS = [
    "Lead",
    "Contacted",
    "Meeting booked",
    "Proposal sent",
    "Won",
    "Lost",
    # Legacy compatibility with existing worker payloads.
    "Proposal",
    "Active",
    "Completed",
]
LEAD_TYPE_OPTIONS = ["Inbound", "Outbound", "Referral", "Previous client"]
PRIORITY_OPTIONS = ["High", "Medium", "Low"]
SOURCE_OPTIONS = [
    "Inbound",
    "Outbound",
    "Referral",
    "Previous client",
    "Direct",
    "Portfolio",
    "Social",
    "Unknown",
]


def canonical_lead_key(name: str, source: str) -> str:
    return f"{name.strip().lower()}::{source.strip().lower()}"


def default_demo_leads() -> list[dict[str, Any]]:
    return [
        {
            "name": "Referral Lead",
            "status": "Lead",
            "lead_type": "Referral",
            "priority": "High",
            "deal_size": 1500,
            "source": "Referral",
            "next_action": "Send intro scope and availability",
            "next_follow_up_date": "2026-03-09",
        },
        {
            "name": "Portfolio Lead",
            "status": "Proposal sent",
            "lead_type": "Inbound",
            "priority": "High",
            "deal_size": 2500,
            "source": "Portfolio",
            "next_action": "Follow up on proposal feedback",
            "next_follow_up_date": "2026-03-10",
        },
        {
            "name": "Direct Lead",
            "status": "Contacted",
            "lead_type": "Outbound",
            "priority": "Medium",
            "deal_size": 3000,
            "source": "Direct",
            "next_action": "Book discovery call",
            "next_follow_up_date": "2026-03-11",
        },
    ]


def _today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


def _parse_iso_date(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        return None


def _option_or_default(value: Any, options: list[str], default: str) -> str:
    text = str(value or "").strip()
    if not text:
        return default
    lowered = text.lower()
    for option in options:
        if option.lower() == lowered:
            return option
    return default


def _to_number(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _rich_text_plain(rich_text: Any) -> str:
    if not isinstance(rich_text, list):
        return ""
    parts: list[str] = []
    for item in rich_text:
        if not isinstance(item, dict):
            continue
        plain_text = str(item.get("plain_text", "")).strip()
        if plain_text:
            parts.append(plain_text)
            continue
        text_obj = item.get("text", {})
        if isinstance(text_obj, dict):
            content = str(text_obj.get("content", "")).strip()
            if content:
                parts.append(content)
    return " ".join(parts).strip()


def _title_plain(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    for item in value:
        if not isinstance(item, dict):
            continue
        plain_text = str(item.get("plain_text", "")).strip()
        if plain_text:
            return plain_text
        text_obj = item.get("text", {})
        if isinstance(text_obj, dict):
            content = str(text_obj.get("content", "")).strip()
            if content:
                return content
    return ""


def _property_obj(props: dict[str, Any], primary_name: str, aliases: list[str] | None = None) -> dict[str, Any]:
    aliases = aliases or []
    candidates = [primary_name, *aliases]

    for key in candidates:
        value = props.get(key)
        if isinstance(value, dict):
            return value

    lowered = {name.lower() for name in candidates}
    for key, value in props.items():
        if not isinstance(value, dict):
            continue
        if str(key).strip().lower() in lowered:
            return value
        value_name = str(value.get("name", "")).strip().lower()
        if value_name and value_name in lowered:
            return value

    return {}


def _select_or_status_name(prop: dict[str, Any]) -> str:
    if not isinstance(prop, dict):
        return ""
    status_name = str((prop.get("status") or {}).get("name", "")).strip()
    if status_name:
        return status_name
    return str((prop.get("select") or {}).get("name", "")).strip()


def _date_start(prop: dict[str, Any]) -> str | None:
    if not isinstance(prop, dict):
        return None
    value = prop.get("date")
    if isinstance(value, dict):
        start = str(value.get("start", "")).strip()
        return start or None
    return None


def _number_value(prop: dict[str, Any]) -> float | None:
    if not isinstance(prop, dict):
        return None
    if prop.get("number") is not None:
        return _to_number(prop.get("number"))
    formula = prop.get("formula")
    if isinstance(formula, dict) and formula.get("type") == "number":
        return _to_number(formula.get("number"))
    return None


def _text_value(prop: dict[str, Any]) -> str:
    if not isinstance(prop, dict):
        return ""
    rich = prop.get("rich_text")
    if isinstance(rich, list):
        return _rich_text_plain(rich)
    title = prop.get("title")
    if isinstance(title, list):
        return _title_plain(title)
    return ""


def normalize_lead_payload(lead: dict[str, Any]) -> dict[str, Any]:
    name = str(lead.get("name") or lead.get("Name") or "").strip() or "Unnamed Lead"
    source = str(lead.get("source") or lead.get("Source") or "Unknown").strip() or "Unknown"
    source = _option_or_default(source, SOURCE_OPTIONS, "Unknown")

    status_raw = lead.get("status") or lead.get("Status")
    # Back-compat mapping from old status vocabulary.
    status_alias = {
        "proposal": "Proposal sent",
        "active": "Meeting booked",
        "completed": "Won",
    }
    status_text = str(status_raw or "").strip()
    if status_text.lower() in status_alias:
        status_text = status_alias[status_text.lower()]
    status = _option_or_default(status_text, STATUS_OPTIONS, "Lead")

    lead_type_raw = lead.get("lead_type") or lead.get("leadType") or lead.get("Lead type")
    if not lead_type_raw:
        if source in {"Inbound", "Outbound", "Referral", "Previous client"}:
            lead_type_raw = source
        elif source == "Direct":
            lead_type_raw = "Outbound"
        else:
            lead_type_raw = "Inbound"
    lead_type = _option_or_default(lead_type_raw, LEAD_TYPE_OPTIONS, "Inbound")

    priority = _option_or_default(
        lead.get("priority") or lead.get("Priority"),
        PRIORITY_OPTIONS,
        "Medium",
    )

    normalized = {
        "name": name,
        "status": status,
        "lead_type": lead_type,
        "priority": priority,
        "deal_size": _to_number(lead.get("deal_size", lead.get("value", lead.get("Deal size", 0)))),
        "last_contact": _parse_iso_date(lead.get("last_contact", lead.get("Last contact"))),
        "next_action": str(lead.get("next_action", lead.get("Next action", ""))).strip(),
        "next_follow_up_date": _parse_iso_date(
            lead.get("next_follow_up_date", lead.get("Next follow-up date"))
        ),
        "email_handle": str(lead.get("email_handle", lead.get("Email / handle", ""))).strip(),
        "source": source,
        "notes": str(lead.get("notes", lead.get("Notes", ""))).strip(),
    }
    normalized["lead_key"] = (
        str(lead.get("lead_key", "")).strip()
        or canonical_lead_key(normalized["name"], normalized["source"])
    )
    return normalized


@dataclass
class NotionApiError(Exception):
    status: int
    message: str
    payload: dict[str, Any]

    def __str__(self) -> str:
        return f"Notion API error {self.status}: {self.message}"


class NotionLeadsService:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.environ.get("NOTION_INTEGRATION_SECRET", "").strip()

    def is_configured(self) -> bool:
        return bool(self.token)

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise ValueError("NOTION_INTEGRATION_SECRET not configured")
        return {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{NOTION_API_BASE}{path}"
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(
                method=method.upper(),
                url=url,
                headers=self._headers(),
                params=query,
                data=json.dumps(payload) if payload is not None else None,
            ) as response:
                raw = await response.text()
                body: dict[str, Any]
                if raw:
                    try:
                        parsed = json.loads(raw)
                        body = parsed if isinstance(parsed, dict) else {"data": parsed}
                    except json.JSONDecodeError:
                        body = {"raw": raw}
                else:
                    body = {}

                if response.status >= 400:
                    message = str(body.get("message", body.get("raw", "request failed")))
                    raise NotionApiError(status=response.status, message=message, payload=body)
                return body

    async def discover_parent_page(self) -> str | None:
        result = await self._request(
            "POST",
            "/search",
            payload={
                "query": "",
                "filter": {"property": "object", "value": "page"},
                "page_size": 1,
            },
        )
        results = result.get("results", [])
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, dict):
                return str(first.get("id", "")).strip() or None
        return None

    async def find_database_by_title(self, database_title: str) -> dict[str, Any] | None:
        result = await self._request(
            "POST",
            "/search",
            payload={
                "query": database_title,
                "filter": {"property": "object", "value": "database"},
                "page_size": 20,
            },
        )
        for item in result.get("results", []):
            if not isinstance(item, dict):
                continue
            title = _title_plain(item.get("title", []))
            if title.strip().lower() == database_title.strip().lower():
                return item
        return None

    async def ensure_workspace(
        self,
        *,
        parent_page_id: str | None,
        database_title: str = "Leads",
        data_source_title: str = "Theo Leads",
        database_id: str | None = None,
        data_source_id: str | None = None,
    ) -> dict[str, Any]:
        reused = False
        db_id = (database_id or "").strip()

        if not db_id:
            existing = await self.find_database_by_title(database_title)
            if existing:
                db_id = str(existing.get("id", "")).strip()
                reused = True

        if not db_id:
            parent_id = (parent_page_id or "").strip() or await self.discover_parent_page()
            if not parent_id:
                raise ValueError("No parent page available to create Notion leads database")
            created = await self._request(
                "POST",
                "/databases",
                payload={
                    "parent": {"type": "page_id", "page_id": parent_id},
                    "title": [{"type": "text", "text": {"content": database_title}}],
                },
            )
            db_id = str(created.get("id", "")).strip()
            reused = False

        database = await self._request("GET", f"/databases/{db_id}")
        data_sources = database.get("data_sources", [])
        if not isinstance(data_sources, list) or not data_sources:
            raise ValueError("Database has no data sources; cannot continue")

        ds_id = (data_source_id or "").strip()
        if not ds_id:
            for ds in data_sources:
                if not isinstance(ds, dict):
                    continue
                name = str(ds.get("name", "")).strip()
                if name.lower() == data_source_title.lower():
                    ds_id = str(ds.get("id", "")).strip()
                    break
        if not ds_id and isinstance(data_sources[0], dict):
            ds_id = str(data_sources[0].get("id", "")).strip()

        if not ds_id:
            raise ValueError("Unable to resolve data_source_id")

        await self._request(
            "PATCH",
            f"/data_sources/{ds_id}",
            payload=self._data_source_patch_payload(data_source_title),
        )

        return {
            "database_id": db_id,
            "data_source_id": ds_id,
            "database_title": database_title,
            "data_source_title": data_source_title,
            "reused": reused,
            "schema_version": SCHEMA_VERSION,
            "database_url": f"https://www.notion.so/{db_id.replace('-', '')}",
        }

    async def _status_property_kind_for_data_source(self, data_source_id: str) -> str:
        try:
            data_source = await self._request("GET", f"/data_sources/{data_source_id}")
        except Exception:  # noqa: BLE001
            return "select"
        properties = data_source.get("properties", {})
        if not isinstance(properties, dict):
            return "select"
        status_prop = _property_obj(properties, "Status", aliases=["status"])
        prop_type = str(status_prop.get("type", "")).strip().lower()
        if prop_type == "status" or isinstance(status_prop.get("status"), dict):
            return "status"
        return "select"

    def _data_source_patch_payload(self, data_source_title: str) -> dict[str, Any]:
        return {
            "title": [{"type": "text", "text": {"content": data_source_title}}],
            "properties": {
                "Name": {"title": {}},
                "Status": {"select": {"options": [{"name": s} for s in STATUS_OPTIONS]}},
                "Lead type": {"select": {"options": [{"name": s} for s in LEAD_TYPE_OPTIONS]}},
                "Priority": {"select": {"options": [{"name": s} for s in PRIORITY_OPTIONS]}},
                "Deal size": {"number": {"format": "dollar"}},
                "Last contact": {"date": {}},
                "Next action": {"rich_text": {}},
                "Next follow-up date": {"date": {}},
                "Email / handle": {"rich_text": {}},
                "Source": {"select": {"options": [{"name": s} for s in SOURCE_OPTIONS]}},
                "Notes": {"rich_text": {}},
                "Lead Key": {"rich_text": {}},
            },
        }

    async def query_all_rows(self, data_source_id: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            payload: dict[str, Any] = {"page_size": 100}
            if cursor:
                payload["start_cursor"] = cursor
            result = await self._request("POST", f"/data_sources/{data_source_id}/query", payload=payload)
            batch = result.get("results", [])
            if isinstance(batch, list):
                rows.extend([r for r in batch if isinstance(r, dict)])
            if not result.get("has_more"):
                break
            cursor = str(result.get("next_cursor", "")).strip() or None
            if not cursor:
                break
        return rows

    def row_to_lead(self, row: dict[str, Any]) -> dict[str, Any]:
        properties = row.get("properties", {})
        props = properties if isinstance(properties, dict) else {}

        prop_name = _property_obj(props, "Name", aliases=["name"])
        prop_status = _property_obj(props, "Status", aliases=["status"])
        prop_lead_type = _property_obj(props, "Lead type", aliases=["Lead Type", "lead_type"])
        prop_priority = _property_obj(props, "Priority", aliases=["priority"])
        prop_deal_size = _property_obj(props, "Deal size", aliases=["Deal Size", "deal_size", "Value"])
        prop_last_contact = _property_obj(props, "Last contact", aliases=["Last Contact", "last_contact"])
        prop_next_action = _property_obj(props, "Next action", aliases=["Next Action", "next_action"])
        prop_next_follow_up = _property_obj(
            props,
            "Next follow-up date",
            aliases=["Next Follow-up Date", "next_follow_up_date"],
        )
        prop_email = _property_obj(props, "Email / handle", aliases=["Email", "Handle", "email_handle"])
        prop_source = _property_obj(props, "Source", aliases=["source"])
        prop_notes = _property_obj(props, "Notes", aliases=["notes"])
        prop_lead_key = _property_obj(props, "Lead Key", aliases=["lead_key", "Lead key"])

        name = _text_value(prop_name)
        status = _select_or_status_name(prop_status)
        lead_type = _select_or_status_name(prop_lead_type)
        priority = _select_or_status_name(prop_priority)
        deal_size = _number_value(prop_deal_size)
        last_contact = _date_start(prop_last_contact)
        next_action = _text_value(prop_next_action)
        next_follow_up = _date_start(prop_next_follow_up)
        email_handle = _text_value(prop_email)
        source = _select_or_status_name(prop_source) or _text_value(prop_source)
        notes = _text_value(prop_notes)
        lead_key = _text_value(prop_lead_key)
        if not lead_key:
            lead_key = canonical_lead_key(name or "Unnamed Lead", source or "Unknown")

        return normalize_lead_payload(
            {
                "name": name,
                "status": status,
                "lead_type": lead_type,
                "priority": priority,
                "deal_size": deal_size,
                "last_contact": last_contact,
                "next_action": next_action,
                "next_follow_up_date": next_follow_up,
                "email_handle": email_handle,
                "source": source or "Unknown",
                "notes": notes,
                "lead_key": lead_key,
                "page_id": row.get("id"),
            }
        ) | {"page_id": str(row.get("id", "")).strip()}

    @staticmethod
    def _status_kind_from_row(row: dict[str, Any]) -> str:
        props = row.get("properties", {})
        if not isinstance(props, dict):
            return "select"
        status_prop = _property_obj(props, "Status", aliases=["status"])
        prop_type = str(status_prop.get("type", "")).strip().lower()
        if prop_type == "status" or isinstance(status_prop.get("status"), dict):
            return "status"
        return "select"

    def _lead_to_properties(self, lead: dict[str, Any], status_kind: str = "select") -> dict[str, Any]:
        status_kind = "status" if str(status_kind).strip().lower() == "status" else "select"
        status_value = (
            {"status": {"name": lead["status"]}}
            if status_kind == "status"
            else {"select": {"name": lead["status"]}}
        )
        return {
            "Name": {"title": [{"type": "text", "text": {"content": lead["name"]}}]},
            "Status": status_value,
            "Lead type": {"select": {"name": lead["lead_type"]}},
            "Priority": {"select": {"name": lead["priority"]}},
            "Deal size": {"number": lead["deal_size"]},
            "Last contact": {"date": {"start": lead["last_contact"]}} if lead["last_contact"] else {"date": None},
            "Next action": {
                "rich_text": ([{"type": "text", "text": {"content": lead["next_action"]}}] if lead["next_action"] else [])
            },
            "Next follow-up date": (
                {"date": {"start": lead["next_follow_up_date"]}}
                if lead["next_follow_up_date"]
                else {"date": None}
            ),
            "Email / handle": {
                "rich_text": ([{"type": "text", "text": {"content": lead["email_handle"]}}] if lead["email_handle"] else [])
            },
            "Source": {"select": {"name": lead["source"]}},
            "Notes": {"rich_text": ([{"type": "text", "text": {"content": lead["notes"]}}] if lead["notes"] else [])},
            "Lead Key": {"rich_text": [{"type": "text", "text": {"content": lead["lead_key"]}}]},
        }

    async def create_row(self, data_source_id: str, lead: dict[str, Any], status_kind: str = "select") -> dict[str, Any]:
        row = await self._request(
            "POST",
            "/pages",
            payload={
                "parent": {"type": "data_source_id", "data_source_id": data_source_id},
                "properties": self._lead_to_properties(lead, status_kind=status_kind),
            },
        )
        return row

    async def update_row(self, page_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        return await self._request("PATCH", f"/pages/{page_id}", payload={"properties": properties})

    async def archive_row(self, page_id: str) -> dict[str, Any]:
        return await self._request("PATCH", f"/pages/{page_id}", payload={"in_trash": True})

    async def list_leads(self, data_source_id: str) -> list[dict[str, Any]]:
        rows = await self.query_all_rows(data_source_id)
        leads: list[dict[str, Any]] = []
        for row in rows:
            if bool(row.get("in_trash", False)):
                continue
            leads.append(self.row_to_lead(row))
        return leads

    async def patch_lead(
        self,
        *,
        data_source_id: str,
        lead_key: str,
        patch: dict[str, Any],
    ) -> dict[str, Any]:
        lead_key = lead_key.strip().lower()
        if not lead_key:
            raise ValueError("lead_key is required")

        rows = await self.query_all_rows(data_source_id)
        target: dict[str, Any] | None = None
        current_lead: dict[str, Any] | None = None
        for row in rows:
            if bool(row.get("in_trash", False)):
                continue
            lead = self.row_to_lead(row)
            if lead.get("lead_key", "").lower() == lead_key:
                target = row
                current_lead = lead
                break
        if target is None or current_lead is None:
            raise ValueError(f"lead_key not found: {lead_key}")

        status_kind = self._status_kind_from_row(target)
        merged = dict(current_lead)
        merged.update(patch)
        merged = normalize_lead_payload(merged)
        properties = self._lead_to_properties(merged, status_kind=status_kind)
        await self.update_row(str(target.get("id", "")), properties)
        return {"lead_key": merged["lead_key"], "page_id": str(target.get("id", "")), "lead": merged}

    async def sync_leads(
        self,
        *,
        data_source_id: str,
        leads: list[dict[str, Any]],
        strict_reconcile: bool = True,
    ) -> dict[str, Any]:
        desired_by_key: dict[str, dict[str, Any]] = {}
        for raw in leads:
            if not isinstance(raw, dict):
                continue
            normalized = normalize_lead_payload(raw)
            desired_by_key[normalized["lead_key"]] = normalized

        existing_rows = await self.query_all_rows(data_source_id)
        status_kind = "select"
        if existing_rows:
            status_kind = self._status_kind_from_row(existing_rows[0])
        else:
            status_kind = await self._status_property_kind_for_data_source(data_source_id)
        existing_by_key: dict[str, dict[str, Any]] = {}
        page_id_by_key: dict[str, str] = {}
        for row in existing_rows:
            if bool(row.get("in_trash", False)):
                continue
            lead = self.row_to_lead(row)
            key = lead["lead_key"]
            existing_by_key[key] = lead
            page_id_by_key[key] = str(row.get("id", ""))

        created_keys: list[str] = []
        updated_keys: list[str] = []
        noop_keys: list[str] = []
        archived_keys: list[str] = []

        managed_fields = [
            "name",
            "status",
            "lead_type",
            "priority",
            "deal_size",
            "last_contact",
            "next_action",
            "next_follow_up_date",
            "email_handle",
            "source",
            "notes",
            "lead_key",
        ]

        for key in sorted(desired_by_key):
            desired = desired_by_key[key]
            existing = existing_by_key.get(key)
            if existing is None:
                await self.create_row(data_source_id, desired, status_kind=status_kind)
                created_keys.append(key)
                continue

            changed = any(existing.get(field) != desired.get(field) for field in managed_fields)
            if changed:
                await self.update_row(page_id_by_key[key], self._lead_to_properties(desired, status_kind=status_kind))
                updated_keys.append(key)
            else:
                noop_keys.append(key)

        if strict_reconcile:
            stale = sorted(set(existing_by_key) - set(desired_by_key))
            for key in stale:
                page_id = page_id_by_key.get(key, "")
                if not page_id:
                    continue
                await self.archive_row(page_id)
                archived_keys.append(key)

        return {
            "counts": {
                "desired": len(desired_by_key),
                "created": len(created_keys),
                "updated": len(updated_keys),
                "noop": len(noop_keys),
                "archived": len(archived_keys),
            },
            "created_keys": created_keys,
            "updated_keys": updated_keys,
            "noop_keys": noop_keys,
            "archived_keys": archived_keys,
            "strict_reconcile": strict_reconcile,
            "generated_at": _today_iso(),
        }


_notion_leads_service: NotionLeadsService | None = None


def get_notion_leads_service() -> NotionLeadsService:
    global _notion_leads_service
    if _notion_leads_service is None:
        _notion_leads_service = NotionLeadsService()
    return _notion_leads_service
