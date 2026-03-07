"""Planner-facing mirrored snapshot files for live Notion refreshes."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MIRROR_FILENAMES: dict[str, str] = {
    "notion_leads": "notion_leads.jsonl",
    "time_commitments": "time_commitments.jsonl",
    "budget_commitments": "budget_commitments.jsonl",
}


def persona_data_dir(persona_id: str) -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "all_personas" / f"persona_{persona_id}"


def notion_page_url(page_id: str) -> str:
    clean = str(page_id or "").strip().replace("-", "")
    if not clean:
        return ""
    return f"https://www.notion.so/{clean}"


def _slug(value: str) -> str:
    parts = re.findall(r"[a-z0-9]+", str(value or "").strip().lower())
    return "_".join(parts) or "item"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _dedupe_tags(values: list[str]) -> list[str]:
    out: list[str] = []
    for item in values:
        text = str(item or "").strip().lower()
        if text and text not in out:
            out.append(text)
    return out


def _deal_text(value: Any) -> str:
    try:
        amount = float(value or 0.0)
    except (TypeError, ValueError):
        amount = 0.0
    if amount <= 0:
        return "unsized deal"
    if amount.is_integer():
        return f"${int(amount)}"
    return f"${amount:.2f}"


def _lead_lane(status: str) -> str:
    status_key = str(status or "").strip().lower()
    if status_key == "won":
        return "won"
    if status_key == "lost":
        return "lost"
    return "pipeline"


def _stable_run_id(payload: dict[str, Any]) -> str:
    digest = sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return f"run_{digest[:16]}"


def build_notion_lead_snapshot_rows(
    leads: list[dict[str, Any]],
    *,
    run_id: str,
    origin: str = "live_webhook",
    refreshed_at: str | None = None,
) -> list[dict[str, Any]]:
    ordered = sorted(
        (lead for lead in leads if isinstance(lead, dict)),
        key=lambda lead: (
            str(lead.get("lead_key", "")).strip().lower(),
            str(lead.get("name", "")).strip().lower(),
            str(lead.get("page_id", "")).strip().lower(),
        ),
    )
    rows: list[dict[str, Any]] = []
    for lead in ordered:
        page_id = str(lead.get("page_id", "")).strip()
        name = str(lead.get("name", "")).strip() or "Unnamed Lead"
        status = str(lead.get("status", "")).strip() or "Lead"
        priority = str(lead.get("priority", "")).strip() or "Medium"
        source = str(lead.get("source", "")).strip() or "notion"
        next_action = str(lead.get("next_action", "")).strip()
        follow_up = str(lead.get("next_follow_up_date", "")).strip()
        last_contact = str(lead.get("last_contact", "")).strip()
        lead_key = str(lead.get("lead_key", "")).strip() or f"{name.lower()}::{source.lower()}"
        deal_size = lead.get("deal_size", 0)
        material_payload = {
            "lead_key": lead_key,
            "name": name,
            "status": status,
            "priority": priority,
            "deal_size": deal_size,
            "next_action": next_action,
            "next_follow_up_date": follow_up,
            "last_contact": last_contact,
            "page_id": page_id,
        }
        text = (
            f"{name} [{status}] {priority} priority, { _deal_text(deal_size) }. "
            f"Next action: {next_action or 'none recorded'}."
        )
        if follow_up:
            text += f" Follow up by {follow_up}."

        row = {
            "id": f"nl_{_slug(lead_key)}",
            "ts": follow_up or last_contact or refreshed_at or "",
            "text": text,
            "tags": _dedupe_tags(
                [
                    "notion",
                    "lead",
                    status,
                    priority,
                    source,
                    _lead_lane(status),
                ]
            ),
            "source": "notion",
            "origin": origin,
            "run_id": _stable_run_id(material_payload),
            "external_url": notion_page_url(page_id),
            "notion_page_id": page_id,
            "lead_key": lead_key,
            "name": name,
            "status": status,
            "priority": priority,
            "deal_size": deal_size,
            "next_action": next_action,
            "next_follow_up_date": follow_up or None,
            "win_probability": lead.get("win_probability"),
            "trust_risk": lead.get("trust_risk"),
            "lane": _lead_lane(status),
        }
        rows.append(row)
    return rows


def _empty_snapshot_rows() -> list[dict[str, Any]]:
    return []


def write_jsonl_snapshot(path: Path, rows: list[dict[str, Any]]) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = ""
    if rows:
        content = "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in rows)
    previous = path.read_text() if path.exists() else None
    if previous == content:
        return False
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content)
    tmp_path.replace(path)
    return True


def write_notion_mirror_snapshots(
    *,
    persona_id: str,
    leads: list[dict[str, Any]],
    run_id: str,
    origin: str = "live_webhook",
    refreshed_at: str | None = None,
) -> dict[str, dict[str, Any]]:
    root = persona_data_dir(persona_id)
    lead_rows = build_notion_lead_snapshot_rows(
        leads,
        run_id=run_id,
        origin=origin,
        refreshed_at=refreshed_at,
    )
    mirror_rows = {
        "notion_leads": lead_rows,
        "time_commitments": _empty_snapshot_rows(),
        "budget_commitments": _empty_snapshot_rows(),
    }

    results: dict[str, dict[str, Any]] = {}
    for domain, rows in mirror_rows.items():
        filename = MIRROR_FILENAMES[domain]
        path = root / filename
        changed = write_jsonl_snapshot(path, rows)
        results[domain] = {
            "domain": domain,
            "file": filename,
            "path": str(path),
            "rows": len(rows),
            "changed": changed,
        }
    return results
