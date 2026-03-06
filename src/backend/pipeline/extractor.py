"""Deterministic extractor — reads persona JSONL files into compact typed structs.

No LLM calls here. Output must stay under ~8k tokens.

Per-domain functions are exported so AnalysisCache can re-extract a single
domain without re-reading all files.
"""
import json
from collections import defaultdict
from datetime import datetime
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


# ---------------------------------------------------------------------------
# Full extractor (backward-compatible, calls per-domain functions)
# ---------------------------------------------------------------------------

def extract_persona_data(persona_id: str = "p01") -> dict:
    profile = extract_profile(persona_id)
    transactions_summary, transactions = extract_transactions(persona_id)
    calendar_summary, calendar_records = extract_calendar_data(persona_id)
    lifelog_summary, lifelog = extract_lifelog(persona_id)
    social_summary, social = extract_social(persona_id)

    data_refs: dict[str, str] = {}
    for records in [calendar_records, transactions, lifelog, social]:
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
        "data_refs": data_refs,
    }
