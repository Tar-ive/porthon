"""Action planner — quest recommendation core.

Given a selected scenario + extracted persona data, generates 3-5 time-bound actions
each citing a specific record id from data_refs.
"""
import json
import os

from openai import AsyncOpenAI


def _build_prompt(scenario: dict, extracted: dict) -> str:
    profile = extracted["profile"]
    goals = "\n".join(f"  - {g}" for g in profile.get("goals", []))

    # Recent calendar events (next available — we use most recent since data is historical)
    cal_records = extracted.get("calendar", {})
    # Pull actual records from data_refs that are cal_ ids
    data_refs = extracted.get("data_refs", {})
    cal_refs = {k: v for k, v in data_refs.items() if k.startswith("cal_")}
    # Take last 10 calendar entries by id sort (highest id = most recent in synthetic data)
    recent_cal = sorted(cal_refs.items(), key=lambda x: x[0], reverse=True)[:10]
    cal_str = "\n".join(f"  [{rid}] {text}" for rid, text in recent_cal)

    # Recent transactions
    tx_refs = {k: v for k, v in data_refs.items() if k.startswith("t_")}
    recent_tx = sorted(tx_refs.items(), key=lambda x: x[0], reverse=True)[:10]
    tx_str = "\n".join(f"  [{rid}] {text}" for rid, text in recent_tx)

    # Recent lifelog
    ll = extracted.get("lifelog", {})
    recent_ll = ll.get("recent", [])
    ll_str = "\n".join(f"  [{e['id']}] {e['text'][:120]}" for e in recent_ll[:5])

    available_ids = (
        [rid for rid, _ in recent_cal]
        + [rid for rid, _ in recent_tx]
        + [e["id"] for e in recent_ll[:5]]
    )
    ids_list = ", ".join(available_ids)

    return f"""Persona: {profile['name']}, {profile['job']}

Goals:
{goals}

Selected scenario: "{scenario['title']}" ({scenario['horizon']}, {scenario['likelihood']})
Scenario summary: {scenario['summary']}

Recent calendar events:
{cal_str}

Recent transactions:
{tx_str}

Recent lifelog entries:
{ll_str}

Available record IDs to cite: {ids_list}

Generate 3-5 concrete, time-bound action recommendations to move {profile['name']} toward this scenario.

Rules:
1. Each action MUST cite a real record ID from the list above as data_ref
2. Actions must be specific and time-bound (NOT "exercise more" — instead "Block 6–6:30pm Monday for a 30min run — cal_XXXX shows that slot is free")
3. Connect each action to at least one cross-domain pattern (e.g. how fixing sleep also improves career focus)
4. Reference the scenario outcome in each rationale

Return a JSON object:
{{
  "scenario_id": "{scenario['id']}",
  "actions": [
    {{
      "action": "specific time-bound action description",
      "rationale": "1-2 sentences linking to a detected pattern and the scenario outcome",
      "data_ref": "one real record id from the available list above",
      "compound_summary": "how this action compounds toward the scenario over 1-3 years"
    }}
  ]
}}"""


async def generate_actions(scenario: dict, extracted: dict) -> dict:
    client = AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL") or None,
    )
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    prompt = _build_prompt(scenario, extracted)

    response = await client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a personal life coach generating a concrete action plan grounded in "
                    "real behavioral data. Every action must cite a specific record ID from the "
                    "data provided. Return ONLY valid JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=1500,
    )

    raw = response.choices[0].message.content or "{}"
    parsed = json.loads(raw)

    # Normalize
    return {
        "scenario_id": parsed.get("scenario_id", scenario.get("id", "")),
        "actions": parsed.get("actions", []),
    }
