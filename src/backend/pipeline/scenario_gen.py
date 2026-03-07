"""Scenario generator — calls LLM to produce 3 life scenarios from extracted persona data."""
import json
import os

from openai import AsyncOpenAI


def _build_prompt(extracted: dict, kg_snippets: list | None = None) -> str:
    profile = extracted["profile"]
    goals = "\n".join(f"  - {g}" for g in profile.get("goals", []))
    pain_points = "\n".join(f"  - {p}" for p in profile.get("pain_points", []))

    # Summarize transaction categories
    tx = extracted.get("transactions", {})
    # Aggregate across all weeks
    category_totals: dict[str, float] = {}
    for week_data in tx.values():
        for cat, amt in week_data.items():
            category_totals[cat] = category_totals.get(cat, 0) + amt
    top_spend = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:6]
    spend_str = ", ".join(f"{cat}: ${amt:.0f}" for cat, amt in top_spend)

    # Calendar density
    cal = extracted.get("calendar", {})
    top_cal_tags = cal.get("top_tags", {})
    cal_tags_str = ", ".join(f"{t}({n})" for t, n in list(top_cal_tags.items())[:5])

    # Lifelog top signals
    ll = extracted.get("lifelog", {})
    top_ll_tags = ll.get("top_tags", {})
    ll_tags_str = ", ".join(f"{t}({n})" for t, n in list(top_ll_tags.items())[:8])

    # Recent lifelog entries
    recent_ll = ll.get("recent", [])
    recent_ll_str = "\n".join(f"  [{e['id']}] {e['text'][:120]}" for e in recent_ll[:3])

    notion = extracted.get("notion_leads", {})
    status_counts = notion.get("status_counts", {})
    pipeline_status_str = ", ".join(f"{status}({count})" for status, count in status_counts.items()) or "none"
    open_pipeline_value = float(notion.get("open_pipeline_value", 0) or 0)
    due_followups = notion.get("due_followups", [])
    due_followups_str = "\n".join(
        f"  [{item['id']}] {item['name']} due {item['next_follow_up_date']} ({item['priority']}, ${item['deal_size']:.0f})"
        for item in due_followups[:4]
    ) or "  none due soon"

    time_commitments = extracted.get("time_commitments", {})
    open_minutes = int(time_commitments.get("total_minutes_open", 0) or 0)
    due_soon_commitments = time_commitments.get("due_soon", [])
    due_soon_commitments_str = "\n".join(
        f"  [{item['id']}] {item['title']} due {item['due_date']} ({item['estimated_minutes']} min)"
        for item in due_soon_commitments[:4]
    ) or "  no near-term commitments"

    budget = extracted.get("budget_commitments", {})
    inflow_total = float(budget.get("open_inflow_total", 0) or 0)
    outflow_total = float(budget.get("open_outflow_total", 0) or 0)
    net_pressure = float(budget.get("net_open_pressure", 0) or 0)
    high_pressure = budget.get("high_pressure", [])
    high_pressure_str = "\n".join(
        f"  [{item['id']}] {item['title']} {item['direction']} ${item['amount']:.0f} ({item['pressure_level']})"
        for item in high_pressure[:4]
    ) or "  no high-pressure budget items"

    # KG memory context (cross-domain patterns retrieved from knowledge graph)
    kg_section = ""
    if kg_snippets:
        kg_lines = "\n".join(f"  - {s}" for s in kg_snippets[:6])
        kg_section = f"\nKnowledge graph memory (cross-domain patterns):\n{kg_lines}\n"

    return f"""Persona: {profile['name']}, {profile['job']}, {profile['income']}

Goals:
{goals}

Pain points:
{pain_points}

Behavioral signals:
- Top spending categories (aggregate): {spend_str}
- Calendar top tags: {cal_tags_str}
- Lifelog top tags: {ll_tags_str}
- Open pipeline value: ${open_pipeline_value:.0f}
- Pipeline status mix: {pipeline_status_str}
- Open scheduled commitment load: {open_minutes} minutes
- Open budget pressure: inflow ${inflow_total:.0f} vs outflow ${outflow_total:.0f} (net {net_pressure:+.0f})

Recent lifelog entries:
{recent_ll_str}

Due-soon lead follow-ups:
{due_followups_str}

Due-soon time commitments:
{due_soon_commitments_str}

High-pressure budget commitments:
{high_pressure_str}
{kg_section}
Generate exactly 3 life scenarios for this person. Each must:
- Cover a different time horizon (1yr, 5yr, 10yr — one each)
- Have a different likelihood (most_likely, possible, aspirational — one each)
- Reference ≥2 cross-domain behavioral patterns (e.g. career+health, finance+relationship)
- Consider pipeline pressure, time load, and inflow/outflow pressure when relevant
- Be grounded in the stated goals above
- Include 2-4 relevant tags

Return a JSON array with exactly 3 objects. Each object:
{{
  "id": "scen_001",   // scen_001, scen_002, scen_003
  "title": "short title",
  "horizon": "1yr" | "5yr" | "10yr",
  "likelihood": "most_likely" | "possible" | "aspirational",
  "summary": "2-3 sentence description grounded in this person's goals and data",
  "tags": ["tag1", "tag2"],
  "pattern_ids": ["pattern_label_1", "pattern_label_2"]  // invented cross-domain labels
}}"""


async def generate_scenarios(extracted: dict, kg_snippets: list | None = None) -> list[dict]:
    client = AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL") or None,
    )
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    prompt = _build_prompt(extracted, kg_snippets=kg_snippets)

    response = await client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a life scenario planner. You analyze behavioral data and produce "
                    "grounded, specific life trajectory scenarios in JSON. "
                    "Return ONLY valid JSON — a single object with a 'scenarios' key containing an array."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=1200,
    )

    raw = response.choices[0].message.content or "{}"
    parsed = json.loads(raw)

    # Handle both {"scenarios": [...]} and bare [...]
    if isinstance(parsed, list):
        scenarios = parsed
    else:
        scenarios = parsed.get("scenarios", list(parsed.values())[0] if parsed else [])

    # Validate and normalize
    valid = []
    for i, s in enumerate(scenarios[:3]):
        valid.append(
            {
                "id": s.get("id", f"s_{i+1:03d}"),
                "title": s.get("title", "Scenario"),
                "horizon": s.get("horizon", "5yr"),
                "likelihood": s.get("likelihood", "possible"),
                "summary": s.get("summary", ""),
                "tags": s.get("tags", []),
                "pattern_ids": s.get("pattern_ids", []),
            }
        )

    return valid
