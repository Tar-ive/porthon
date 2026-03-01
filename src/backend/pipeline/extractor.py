"""Deterministic extractor — reads p01 JSONL files into a compact typed struct.

No LLM calls here. Output must stay under ~8k tokens.
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


def extract_persona_data(persona_id: str = "p01") -> dict:
    root = _data_root(persona_id)

    # --- Profile ---
    profile_path = root / "persona_profile.json"
    profile_raw = json.loads(profile_path.read_text()) if profile_path.exists() else {}
    profile = {
        "name": profile_raw.get("name", "Unknown"),
        "job": profile_raw.get("job", ""),
        "income": profile_raw.get("income_approx", ""),
        "goals": profile_raw.get("goals", []),
        "pain_points": profile_raw.get("pain_points", []),
        "personality": profile_raw.get("personality", {}),
    }

    # --- Transactions: weekly totals by category ---
    transactions = _read_jsonl(root / "transactions.jsonl")
    weekly_spend: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for t in transactions:
        ts = t.get("ts", "")
        tags = t.get("tags", [])
        text = t.get("text", "")
        # Extract dollar amount from text like "$85.00 - Easy Tiger - social"
        amount = 0.0
        if text.startswith("$"):
            try:
                amount = float(text[1:].split(" ")[0].replace(",", ""))
            except ValueError:
                pass
        if ts and tags:
            # ISO week key: YYYY-Www
            try:
                dt = datetime.fromisoformat(ts)
                week_key = dt.strftime("%Y-W%V")
                category = tags[0]
                weekly_spend[week_key][category] += amount
            except ValueError:
                pass

    # Keep most recent 12 weeks
    sorted_weeks = sorted(weekly_spend.keys(), reverse=True)[:12]
    transactions_summary = {w: dict(weekly_spend[w]) for w in sorted_weeks}

    # --- Calendar: weekly event count + top tag frequencies ---
    calendar = _read_jsonl(root / "calendar.jsonl")
    cal_tag_freq: dict[str, int] = defaultdict(int)
    weekly_event_count: dict[str, int] = defaultdict(int)
    for ev in calendar:
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
    calendar_summary = {
        "weekly_event_counts": {w: weekly_event_count[w] for w in sorted_cal_weeks},
        "top_tags": dict(top_cal_tags),
    }

    # --- Lifelog: top tag frequencies + 5 most recent entries ---
    lifelog = _read_jsonl(root / "lifelog.jsonl")
    ll_tag_freq: dict[str, int] = defaultdict(int)
    for entry in lifelog:
        for tag in entry.get("tags", []):
            ll_tag_freq[tag] += 1

    top_ll_tags = sorted(ll_tag_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    recent_lifelog = sorted(lifelog, key=lambda x: x.get("ts", ""), reverse=True)[:5]
    lifelog_summary = {
        "top_tags": dict(top_ll_tags),
        "recent": [
            {"id": e["id"], "text": e["text"], "tags": e.get("tags", [])}
            for e in recent_lifelog
        ],
    }

    # --- Social posts: 5 most recent ---
    social = _read_jsonl(root / "social_posts.jsonl")
    recent_social = sorted(social, key=lambda x: x.get("ts", ""), reverse=True)[:5]
    social_summary = [
        {"id": p["id"], "text": p["text"], "tags": p.get("tags", [])}
        for p in recent_social
    ]

    # --- data_refs: id → text for all records (for action planner citation) ---
    data_refs: dict[str, str] = {}
    for source, records in [
        ("calendar", calendar),
        ("transactions", transactions),
        ("lifelog", lifelog),
        ("social", social),
    ]:
        for r in records:
            rid = r.get("id")
            text = r.get("text", "")
            if rid:
                data_refs[rid] = text

    return {
        "profile": profile,
        "transactions": transactions_summary,
        "calendar": calendar_summary,
        "lifelog": lifelog_summary,
        "social": social_summary,
        "data_refs": data_refs,
    }
