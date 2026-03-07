"""Deterministic extractor — reads persona JSONL files into compact typed structs.

No LLM calls here. Output must stay under ~8k tokens.

Per-domain functions are exported so AnalysisCache can re-extract a single
domain without re-reading all files.
"""
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


def _data_root(persona_id: str) -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "all_personas" / f"persona_{persona_id}"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def _parse_iso_date(value: str | None) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _today() -> date:
    return datetime.now().date()


# ---------------------------------------------------------------------------
# Per-domain extractors (public — used by AnalysisCache for incremental refresh)
# ---------------------------------------------------------------------------

def extract_profile(persona_id: str) -> dict:
    root = _data_root(persona_id)
    profile_path = root / "persona_profile.json"
    profile_raw = json.loads(profile_path.read_text()) if profile_path.exists() else {}
    return {
        "name": profile_raw.get("name", "Unknown"),
        "job": profile_raw.get("job", ""),
        "income": profile_raw.get("income_approx", ""),
        "goals": profile_raw.get("goals", []),
        "pain_points": profile_raw.get("pain_points", []),
        "personality": profile_raw.get("personality", {}),
    }


def extract_transactions(persona_id: str) -> tuple[dict, list]:
    """Returns (transactions_summary, raw_records)."""
    root = _data_root(persona_id)
    transactions = _read_jsonl(root / "transactions.jsonl")
    weekly_spend: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for t in transactions:
        ts = t.get("ts", "")
        tags = t.get("tags", [])
        text = t.get("text", "")
        amount = 0.0
        if text.startswith("$"):
            try:
                amount = float(text[1:].split(" ")[0].replace(",", ""))
            except ValueError:
                pass
        if ts and tags:
            try:
                dt = datetime.fromisoformat(ts)
                week_key = dt.strftime("%Y-W%V")
                category = tags[0]
                weekly_spend[week_key][category] += amount
            except ValueError:
                pass
    sorted_weeks = sorted(weekly_spend.keys(), reverse=True)[:12]
    summary = {w: dict(weekly_spend[w]) for w in sorted_weeks}
    return summary, transactions


def extract_calendar_data(persona_id: str) -> tuple[dict, list]:
    """Returns (calendar_summary, raw_records). Named to avoid shadowing stdlib calendar."""
    root = _data_root(persona_id)
    calendar_records = _read_jsonl(root / "calendar.jsonl")
    cal_tag_freq: dict[str, int] = defaultdict(int)
    weekly_event_count: dict[str, int] = defaultdict(int)
    for ev in calendar_records:
        ts = ev.get("ts", "")
        tags = ev.get("tags", [])
        for tag in tags:
            cal_tag_freq[tag] += 1
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                week_key = dt.strftime("%Y-W%V")
                weekly_event_count[week_key] += 1
            except ValueError:
                pass
    top_cal_tags = sorted(cal_tag_freq.items(), key=lambda x: x[1], reverse=True)[:5]
    sorted_cal_weeks = sorted(weekly_event_count.keys(), reverse=True)[:12]
    summary = {
        "weekly_event_counts": {w: weekly_event_count[w] for w in sorted_cal_weeks},
        "top_tags": dict(top_cal_tags),
    }
    return summary, calendar_records


def extract_lifelog(persona_id: str) -> tuple[dict, list]:
    """Returns (lifelog_summary, raw_records)."""
    root = _data_root(persona_id)
    lifelog = _read_jsonl(root / "lifelog.jsonl")
    ll_tag_freq: dict[str, int] = defaultdict(int)
    for entry in lifelog:
        for tag in entry.get("tags", []):
            ll_tag_freq[tag] += 1
    top_ll_tags = sorted(ll_tag_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    recent_lifelog = sorted(lifelog, key=lambda x: x.get("ts", ""), reverse=True)[:5]
    summary = {
        "top_tags": dict(top_ll_tags),
        "recent": [
            {"id": e["id"], "text": e["text"], "tags": e.get("tags", [])}
            for e in recent_lifelog
        ],
    }
    return summary, lifelog


def extract_social(persona_id: str) -> tuple[list, list]:
    """Returns (social_summary, raw_records)."""
    root = _data_root(persona_id)
    social = _read_jsonl(root / "social_posts.jsonl")
    recent_social = sorted(social, key=lambda x: x.get("ts", ""), reverse=True)[:5]
    summary = [
        {"id": p["id"], "text": p["text"], "tags": p.get("tags", [])}
        for p in recent_social
    ]
    return summary, social


def extract_notion_leads(persona_id: str) -> tuple[dict, list]:
    """Returns (notion_leads_summary, raw_records)."""
    root = _data_root(persona_id)
    leads = _read_jsonl(root / "notion_leads.jsonl")
    today = _today()

    status_counts: dict[str, int] = defaultdict(int)
    open_pipeline_value = 0.0
    due_followups: list[dict] = []
    top_leads: list[dict] = []

    for lead in leads:
        status = str(lead.get("status", "")).strip() or "Lead"
        status_counts[status] += 1
        deal_size = float(lead.get("deal_size", 0) or 0)
        if status not in {"Won", "Lost"}:
            open_pipeline_value += deal_size
        follow_up = _parse_iso_date(str(lead.get("next_follow_up_date", "")).strip())
        lead_item = {
            "id": str(lead.get("id", "")).strip(),
            "name": str(lead.get("name", "")).strip(),
            "status": status,
            "priority": str(lead.get("priority", "")).strip(),
            "deal_size": deal_size,
            "next_follow_up_date": follow_up.isoformat() if follow_up else "",
            "text": str(lead.get("text", "")).strip(),
        }
        top_leads.append(lead_item)
        if follow_up is not None and follow_up <= (today + timedelta(days=7)) and status not in {"Won", "Lost"}:
            due_followups.append(lead_item)

    due_followups.sort(
        key=lambda item: (
            item["next_follow_up_date"] or "9999-12-31",
            -(item["deal_size"] or 0),
        )
    )
    top_leads.sort(key=lambda item: (-(item["deal_size"] or 0), item["name"]))

    summary = {
        "status_counts": dict(status_counts),
        "open_pipeline_value": round(open_pipeline_value, 2),
        "due_followups": due_followups[:5],
        "top_leads": top_leads[:5],
        "open_lead_count": sum(
            count for status, count in status_counts.items() if status not in {"Won", "Lost"}
        ),
    }
    return summary, leads


def extract_time_commitments(persona_id: str) -> tuple[dict, list]:
    """Returns (time_commitments_summary, raw_records)."""
    root = _data_root(persona_id)
    commitments = _read_jsonl(root / "time_commitments.jsonl")
    today = _today()

    status_counts: dict[str, int] = defaultdict(int)
    total_minutes_open = 0
    due_soon: list[dict] = []
    blocked: list[dict] = []

    for item in commitments:
        status = str(item.get("status", "")).strip() or "Inbox"
        status_counts[status] += 1
        estimated = int(item.get("estimated_minutes", 0) or 0)
        if status not in {"Done", "Dropped"}:
            total_minutes_open += estimated
        due_date = _parse_iso_date(str(item.get("due_date", "")).strip())
        commitment = {
            "id": str(item.get("id", "")).strip(),
            "title": str(item.get("title", "")).strip(),
            "status": status,
            "priority": str(item.get("priority", "")).strip(),
            "due_date": due_date.isoformat() if due_date else "",
            "estimated_minutes": estimated,
            "text": str(item.get("text", "")).strip(),
        }
        if status == "Blocked":
            blocked.append(commitment)
        if due_date is not None and due_date <= (today + timedelta(days=7)) and status not in {"Done", "Dropped"}:
            due_soon.append(commitment)

    due_soon.sort(key=lambda item: (item["due_date"] or "9999-12-31", -(item["estimated_minutes"] or 0)))
    blocked.sort(key=lambda item: (item["due_date"] or "9999-12-31", item["title"]))

    summary = {
        "status_counts": dict(status_counts),
        "total_minutes_open": total_minutes_open,
        "due_soon": due_soon[:5],
        "blocked": blocked[:5],
        "open_commitment_count": sum(
            count for status, count in status_counts.items() if status not in {"Done", "Dropped"}
        ),
    }
    return summary, commitments


def extract_budget_commitments(persona_id: str) -> tuple[dict, list]:
    """Returns (budget_commitments_summary, raw_records)."""
    root = _data_root(persona_id)
    budgets = _read_jsonl(root / "budget_commitments.jsonl")
    today = _today()

    status_counts: dict[str, int] = defaultdict(int)
    inflow_open = 0.0
    outflow_open = 0.0
    high_pressure: list[dict] = []
    due_soon: list[dict] = []

    for item in budgets:
        status = str(item.get("status", "")).strip() or "Planned"
        status_counts[status] += 1
        amount = float(item.get("amount", 0) or 0)
        direction = str(item.get("direction", "")).strip() or "outflow"
        if status not in {"Paid", "Cancelled"}:
            if direction == "inflow":
                inflow_open += amount
            else:
                outflow_open += amount
        due_date = _parse_iso_date(str(item.get("due_date", "")).strip())
        budget = {
            "id": str(item.get("id", "")).strip(),
            "title": str(item.get("title", "")).strip(),
            "status": status,
            "pressure_level": str(item.get("pressure_level", "")).strip(),
            "direction": direction,
            "amount": amount,
            "due_date": due_date.isoformat() if due_date else "",
            "text": str(item.get("text", "")).strip(),
        }
        if budget["pressure_level"] in {"high", "critical"}:
            high_pressure.append(budget)
        if due_date is not None and due_date <= (today + timedelta(days=7)) and status not in {"Paid", "Cancelled"}:
            due_soon.append(budget)

    due_soon.sort(key=lambda item: (item["due_date"] or "9999-12-31", -(item["amount"] or 0)))
    high_pressure.sort(key=lambda item: (item["pressure_level"] != "critical", -(item["amount"] or 0)))

    summary = {
        "status_counts": dict(status_counts),
        "open_inflow_total": round(inflow_open, 2),
        "open_outflow_total": round(outflow_open, 2),
        "net_open_pressure": round(inflow_open - outflow_open, 2),
        "due_soon": due_soon[:5],
        "high_pressure": high_pressure[:5],
    }
    return summary, budgets


# ---------------------------------------------------------------------------
# Full extractor (backward-compatible, calls per-domain functions)
# ---------------------------------------------------------------------------

def extract_persona_data(persona_id: str = "p01") -> dict:
    profile = extract_profile(persona_id)
    transactions_summary, transactions = extract_transactions(persona_id)
    calendar_summary, calendar_records = extract_calendar_data(persona_id)
    lifelog_summary, lifelog = extract_lifelog(persona_id)
    social_summary, social = extract_social(persona_id)
    notion_leads_summary, notion_leads = extract_notion_leads(persona_id)
    time_commitments_summary, time_commitments = extract_time_commitments(persona_id)
    budget_commitments_summary, budget_commitments = extract_budget_commitments(persona_id)

    data_refs: dict[str, str] = {}
    for records in [
        calendar_records,
        transactions,
        lifelog,
        social,
        notion_leads,
        time_commitments,
        budget_commitments,
    ]:
        for r in records:
            rid = r.get("id")
            if rid:
                data_refs[rid] = r.get("text", "")

    return {
        "profile": profile,
        "transactions": transactions_summary,
        "calendar": calendar_summary,
        "lifelog": lifelog_summary,
        "social": social_summary,
        "notion_leads": notion_leads_summary,
        "time_commitments": time_commitments_summary,
        "budget_commitments": budget_commitments_summary,
        "data_refs": data_refs,
    }
