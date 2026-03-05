"""Lead OS helpers for profile-driven pod scheduling over Notion leads."""

from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

OPEN_STATUSES = {"Lead", "Contacted", "Meeting booked", "Proposal sent"}


def _parse_iso_date(value: Any) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _priority_weight(priority: str) -> float:
    mapping = {"high": 1.0, "medium": 0.6, "low": 0.2}
    return mapping.get(str(priority or "").strip().lower(), 0.4)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _lane_from_lead(lead: dict[str, Any]) -> str:
    lead_type = str(lead.get("lead_type", "")).strip()
    if lead_type in {"Inbound", "Outbound", "Referral", "Previous client"}:
        return lead_type

    source = str(lead.get("source", "")).strip().lower()
    if source == "referral":
        return "Referral"
    if source in {"previous client", "client"}:
        return "Previous client"
    if source in {"outbound", "cold", "direct"}:
        return "Outbound"
    return "Inbound"


def _owner_pod(status: str, lane: str) -> str:
    s = str(status).strip()
    if s == "Lead":
        return "intake_pod"
    if s == "Contacted":
        return "nurture_pod"
    if s in {"Meeting booked", "Proposal sent"}:
        return "close_pod"
    if s in {"Won", "Lost"}:
        return "finance_pod"
    if lane == "Outbound":
        return "intake_pod"
    return "nurture_pod"


def _conversion_confidence(lead: dict[str, Any], lane: str) -> float:
    status_base = {
        "Lead": 0.15,
        "Contacted": 0.30,
        "Meeting booked": 0.55,
        "Proposal sent": 0.72,
        "Won": 1.0,
        "Lost": 0.0,
    }
    base = status_base.get(str(lead.get("status", "")).strip(), 0.2)
    lane_bonus = {
        "Referral": 0.14,
        "Inbound": 0.08,
        "Previous client": 0.12,
        "Outbound": -0.04,
    }.get(lane, 0.0)
    priority_bonus = {
        "high": 0.08,
        "medium": 0.0,
        "low": -0.06,
    }.get(str(lead.get("priority", "")).strip().lower(), 0.0)
    return _clamp(base + lane_bonus + priority_bonus, 0.0, 1.0)


def _trust_risk(lead: dict[str, Any], lane: str) -> float:
    status = str(lead.get("status", "")).strip()
    lane_risk = {
        "Referral": 0.12,
        "Inbound": 0.2,
        "Previous client": 0.1,
        "Outbound": 0.38,
    }.get(lane, 0.24)
    if status in {"Won", "Lost"}:
        return 0.0
    return lane_risk


def _effort_est_minutes(lead: dict[str, Any], owner: str) -> int:
    status = str(lead.get("status", "")).strip()
    if status == "Lead":
        return 20
    if status == "Contacted":
        return 25
    if status == "Meeting booked":
        return 40
    if status == "Proposal sent":
        return 35
    if owner == "finance_pod":
        return 15
    return 20


def _acquisition_cost_est(lane: str) -> float:
    if lane == "Referral":
        return 8.0
    if lane == "Inbound":
        return 12.0
    if lane == "Previous client":
        return 5.0
    if lane == "Outbound":
        return 36.0
    return 15.0


def _resolve_project_root(source_file: str | None = None) -> Path:
    env_root = str(os.environ.get("PORTHON_PROJECT_ROOT", "")).strip()
    if env_root:
        root = Path(env_root).expanduser().resolve()
        if root.exists():
            return root

    base = Path(source_file).resolve() if source_file else Path(__file__).resolve()
    candidates = [base.parent, *base.parents]
    for candidate in candidates:
        if (candidate / "data").exists():
            return candidate

    if len(base.parents) > 1:
        return base.parents[1]
    return base.parent


def _load_profile(persona_id: str) -> dict[str, Any]:
    root = _resolve_project_root()
    candidates = [
        root / "data" / "summaries" / "master_profile.json",
        root / "data" / "all_personas" / f"persona_{persona_id}" / "persona_profile.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text())
            if isinstance(payload, dict):
                return payload
        except (OSError, json.JSONDecodeError):
            continue
    return {}


def _profile_objective(persona_id: str) -> dict[str, Any]:
    profile = _load_profile(persona_id)
    name = str(profile.get("name", "Theo Nakamura")).strip() or "Theo Nakamura"

    avg_revenue = _to_float(
        ((profile.get("data_sources") or {}).get("transactions") or {}).get("avg_monthly_revenue"),
        0.0,
    )
    debt = _to_float(profile.get("debt"), 0.0)

    return {
        "title": "Profile-driven freelance stability",
        "persona_name": name,
        "primary_goal": (
            "Increase conversion and cash reliability without forcing high-anxiety outreach patterns."
        ),
        "constraints": {
            "trust_first": True,
            "ad_hoc_spam_forbidden": True,
            "customer_approval_required_for_irreversible_sends": True,
            "avg_monthly_revenue": avg_revenue,
            "debt": debt,
        },
    }


def figma_actor_file_key(file_key: str, actor_handle: str) -> str:
    return f"{str(file_key).strip().lower()}::{str(actor_handle).strip().lower()}"


def ensure_lead_os_config(raw: dict[str, Any] | None, persona_id: str, now_iso: str) -> dict[str, Any]:
    cfg = dict(raw or {})
    cfg.setdefault("version", "v3")
    cfg.setdefault("persona_id", persona_id)
    cfg.setdefault("objective", _profile_objective(persona_id))
    cfg.setdefault("lead_pcb", {})
    cfg.setdefault("recommended_actions", [])
    cfg.setdefault("dispatch_log", [])
    cfg.setdefault("figma_comment_links", {})
    cfg.setdefault("figma_actor_file_links", {})
    cfg.setdefault(
        "pods",
        {
            "intake_pod": {"status": "ready", "queue_depth": 0, "focus": "ingest and classify"},
            "nurture_pod": {"status": "ready", "queue_depth": 0, "focus": "follow-up cadence"},
            "close_pod": {"status": "ready", "queue_depth": 0, "focus": "proposal progression"},
            "finance_pod": {"status": "ready", "queue_depth": 0, "focus": "sustainability guardrails"},
        },
    )
    cfg["updated_at"] = now_iso
    return cfg


def build_lead_pcb(lead: dict[str, Any], now_iso: str, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    row = dict(existing or {})
    lead_key = str(lead.get("lead_key", "")).strip()
    lane = _lane_from_lead(lead)
    status = str(lead.get("status", "Lead")).strip() or "Lead"
    owner = _owner_pod(status, lane)
    confidence = _conversion_confidence(lead, lane)
    trust_risk = _trust_risk(lead, lane)

    follow_up = _parse_iso_date(lead.get("next_follow_up_date"))
    last_contact = _parse_iso_date(lead.get("last_contact"))
    today = datetime.now(UTC).date()
    overdue_days = 0
    if follow_up is not None:
        overdue_days = max((today - follow_up).days, 0)

    row.update(
        {
            "lead_key": lead_key,
            "name": str(lead.get("name", "")).strip(),
            "status": status,
            "priority": str(lead.get("priority", "Medium")).strip() or "Medium",
            "source": str(lead.get("source", "Unknown")).strip() or "Unknown",
            "lane": lane,
            "owner_pod": owner,
            "deal_size": _to_float(lead.get("deal_size"), 0.0),
            "next_action": str(lead.get("next_action", "")).strip(),
            "next_follow_up_date": follow_up.isoformat() if follow_up else "",
            "last_contact": last_contact.isoformat() if last_contact else "",
            "overdue_days": overdue_days,
            "conversion_confidence": confidence,
            "trust_risk": trust_risk,
            "effort_est_minutes": _effort_est_minutes(lead, owner),
            "acquisition_cost_est": _acquisition_cost_est(lane),
            "response_sla_due_at": follow_up.isoformat() if follow_up else "",
            "updated_at": now_iso,
        }
    )
    return row


def reconcile_leads(cfg: dict[str, Any], leads: list[dict[str, Any]], now_iso: str) -> dict[str, Any]:
    prev = cfg.get("lead_pcb", {})
    if not isinstance(prev, dict):
        prev = {}

    next_pcb: dict[str, Any] = {}
    rows = sorted(
        [l for l in leads if isinstance(l, dict)],
        key=lambda x: str(x.get("lead_key", "")),
    )
    for lead in rows:
        lead_key = str(lead.get("lead_key", "")).strip()
        if not lead_key:
            continue
        next_pcb[lead_key] = build_lead_pcb(lead, now_iso, prev.get(lead_key))

    cfg["lead_pcb"] = next_pcb
    cfg["updated_at"] = now_iso
    return cfg


def _lead_score(row: dict[str, Any]) -> float:
    status = str(row.get("status", "")).strip()
    if status not in OPEN_STATUSES:
        return -1.0

    deal_size = _to_float(row.get("deal_size"), 0.0)
    value_component = _clamp(deal_size / 5000.0, 0.0, 1.8)
    confidence_component = _to_float(row.get("conversion_confidence"), 0.0) * 1.6
    urgency_component = _clamp(_to_float(row.get("overdue_days"), 0.0) / 5.0, 0.0, 1.5)
    priority_component = _priority_weight(str(row.get("priority", ""))) * 1.2
    trust_penalty = _to_float(row.get("trust_risk"), 0.0) * 1.4
    effort_penalty = _clamp(_to_float(row.get("effort_est_minutes"), 0.0) / 120.0, 0.0, 0.6)

    lane_bonus = {
        "Referral": 0.35,
        "Inbound": 0.22,
        "Previous client": 0.30,
        "Outbound": -0.15,
    }.get(str(row.get("lane", "")), 0.0)

    score = value_component + confidence_component + urgency_component + priority_component + lane_bonus
    score -= trust_penalty + effort_penalty
    return round(score, 4)


def build_recommendations(cfg: dict[str, Any], top_n: int = 12) -> list[dict[str, Any]]:
    pcb = cfg.get("lead_pcb", {})
    if not isinstance(pcb, dict):
        return []

    recommendations: list[dict[str, Any]] = []
    for lead_key, row_any in pcb.items():
        if not isinstance(row_any, dict):
            continue
        row = dict(row_any)
        score = _lead_score(row)
        if score < 0:
            continue

        next_step = row.get("next_action") or "Send concise follow-up and propose one next step"
        next_touch = row.get("next_follow_up_date") or datetime.now(UTC).date().isoformat()
        recommendations.append(
            {
                "lead_key": str(lead_key),
                "name": str(row.get("name", "")).strip(),
                "owner_pod": str(row.get("owner_pod", "nurture_pod")),
                "status": str(row.get("status", "Lead")),
                "source": str(row.get("source", "Unknown")),
                "lane": str(row.get("lane", "Inbound")),
                "priority": str(row.get("priority", "Medium")),
                "deal_size": _to_float(row.get("deal_size"), 0.0),
                "conversion_confidence": _to_float(row.get("conversion_confidence"), 0.0),
                "score": score,
                "next_step": str(next_step),
                "next_touch_date": str(next_touch),
            }
        )

    recommendations.sort(
        key=lambda x: (-_to_float(x.get("score"), 0.0), str(x.get("next_touch_date", "")), str(x.get("lead_key", "")))
    )
    return recommendations[: max(1, min(int(top_n), 100))]


def sustainability_snapshot(cfg: dict[str, Any]) -> dict[str, Any]:
    pcb = cfg.get("lead_pcb", {})
    if not isinstance(pcb, dict):
        pcb = {}

    rows = [r for r in pcb.values() if isinstance(r, dict)]
    open_rows = [r for r in rows if str(r.get("status", "")) in OPEN_STATUSES]

    expected_pipeline_value = sum(_to_float(r.get("deal_size"), 0.0) for r in open_rows)
    weighted_pipeline_value = sum(
        _to_float(r.get("deal_size"), 0.0) * _to_float(r.get("conversion_confidence"), 0.0)
        for r in open_rows
    )
    acquisition_cost = sum(_to_float(r.get("acquisition_cost_est"), 0.0) for r in open_rows)
    overdue = len([r for r in open_rows if int(_to_float(r.get("overdue_days"), 0.0)) > 0])

    lane_counts = {
        "Referral": 0,
        "Inbound": 0,
        "Previous client": 0,
        "Outbound": 0,
    }
    for row in open_rows:
        lane = str(row.get("lane", ""))
        if lane in lane_counts:
            lane_counts[lane] += 1

    open_count = max(len(open_rows), 1)
    outbound_share = lane_counts["Outbound"] / open_count
    trust_first_share = (lane_counts["Referral"] + lane_counts["Inbound"] + lane_counts["Previous client"]) / open_count

    efficiency_ratio = weighted_pipeline_value / max(acquisition_cost, 1.0)

    return {
        "open_leads": len(open_rows),
        "expected_pipeline_value": round(expected_pipeline_value, 2),
        "weighted_pipeline_value": round(weighted_pipeline_value, 2),
        "estimated_acquisition_cost": round(acquisition_cost, 2),
        "followup_overdue_count": overdue,
        "lane_distribution": lane_counts,
        "outbound_share": round(outbound_share, 3),
        "trust_first_share": round(trust_first_share, 3),
        "efficiency_ratio": round(efficiency_ratio, 3),
        "sustainability_status": "stable"
        if trust_first_share >= 0.6 and outbound_share <= 0.4 and overdue <= max(2, len(open_rows) // 3)
        else "watch",
    }


def build_pod_snapshot(
    cfg: dict[str, Any],
    recommendations: list[dict[str, Any]],
    runtime_queue: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    pods = cfg.get("pods", {})
    if not isinstance(pods, dict):
        pods = {}

    rec_counts = {
        "intake_pod": 0,
        "nurture_pod": 0,
        "close_pod": 0,
        "finance_pod": 0,
    }
    for item in recommendations:
        owner = str(item.get("owner_pod", ""))
        if owner in rec_counts:
            rec_counts[owner] += 1

    queued_notion = 0
    if isinstance(runtime_queue, list):
        queued_notion = len(
            [
                task
                for task in runtime_queue
                if isinstance(task, dict)
                and str(task.get("worker_id", "")) == "notion_leads_worker"
                and str(task.get("status", "")) in {"pending", "running", "waiting_approval"}
            ]
        )

    out: dict[str, Any] = {}
    for pod_id, rec_depth in rec_counts.items():
        baseline = pods.get(pod_id, {}) if isinstance(pods.get(pod_id, {}), dict) else {}
        status = "active" if rec_depth > 0 or queued_notion > 0 else "ready"
        out[pod_id] = {
            "status": status,
            "queue_depth": rec_depth,
            "worker_queue_depth": queued_notion if pod_id in {"intake_pod", "nurture_pod", "close_pod"} else 0,
            "focus": baseline.get("focus", ""),
        }
    return out
