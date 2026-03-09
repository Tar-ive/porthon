from __future__ import annotations

import json
from pathlib import Path

import pytest

from daemon.analysis_cache import AnalysisCache
from pipeline import action_planner, extractor, scenario_gen


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _seed_persona_dir(root: Path) -> None:
    (root / "persona_profile.json").write_text(
        json.dumps(
            {
                "name": "Theo Nakamura",
                "job": "Freelance designer",
                "income_approx": "$6k/mo",
                "goals": ["Stabilize freelance income", "Protect execution time"],
                "pain_points": ["Cash flow pressure", "Too many follow-ups fall through"],
                "personality": {"focus": "high"},
            }
        )
    )
    _write_jsonl(
        root / "notion_leads.jsonl",
        [
            {
                "id": "nl_novabit",
                "ts": "2026-03-10",
                "text": "NovaBit [Meeting booked] High priority, $2700. Next action: Send discovery recap. Follow up by 2026-03-10.",
                "tags": ["notion", "lead", "meeting booked", "high", "pipeline"],
                "source": "notion",
                "origin": "live_webhook",
                "run_id": "run_1",
                "external_url": "https://www.notion.so/page1",
                "notion_page_id": "page1",
                "lead_key": "novabit::direct",
                "name": "NovaBit",
                "status": "Meeting booked",
                "priority": "High",
                "deal_size": 2700,
                "next_action": "Send discovery recap",
                "next_follow_up_date": "2026-03-10",
                "win_probability": 0.65,
                "trust_risk": 0.2,
                "lane": "pipeline",
            }
        ],
    )
    _write_jsonl(
        root / "time_commitments.jsonl",
        [
            {
                "id": "tc_followup_block",
                "ts": "2026-03-09",
                "text": "Send NovaBit scope follow-up due 2026-03-09 (45 min).",
                "tags": ["time_commitment", "proposal", "high"],
                "title": "Send NovaBit scope follow-up",
                "status": "Ready",
                "commitment_type": "Proposal",
                "priority": "High",
                "due_date": "2026-03-09",
                "execution_window_start": "2026-03-09",
                "execution_window_end": "2026-03-09",
                "estimated_minutes": 45,
                "related_client": "NovaBit",
                "template_key": "follow_up",
                "calendar_url": "",
            }
        ],
    )
    _write_jsonl(
        root / "budget_commitments.jsonl",
        [
            {
                "id": "bc_invoice_gap",
                "ts": "2026-03-11",
                "text": "Invoice follow-up outflow gap due 2026-03-11 for $1800 at high pressure.",
                "tags": ["budget_commitment", "invoice", "high"],
                "title": "Invoice follow-up gap",
                "status": "Due Soon",
                "budget_type": "Invoice follow-up",
                "direction": "inflow",
                "amount": 1800,
                "confidence": 0.75,
                "pressure_level": "high",
                "due_date": "2026-03-11",
                "linked_time_commitment": "tc_followup_block",
                "related_client": "NovaBit",
            }
        ],
    )


@pytest.mark.fast
def test_extract_persona_data_includes_notion_mirror_domains(tmp_path, monkeypatch):
    _seed_persona_dir(tmp_path)
    monkeypatch.setattr(extractor, "_data_root", lambda persona_id: tmp_path)

    extracted = extractor.extract_persona_data("p05")

    assert extracted["notion_leads"]["open_pipeline_value"] == 2700
    assert extracted["time_commitments"]["total_minutes_open"] == 45
    assert extracted["budget_commitments"]["open_inflow_total"] == 1800
    assert "nl_novabit" in extracted["data_refs"]
    assert "tc_followup_block" in extracted["data_refs"]
    assert "bc_invoice_gap" in extracted["data_refs"]


@pytest.mark.fast
def test_prompt_builders_include_notion_domains(tmp_path, monkeypatch):
    _seed_persona_dir(tmp_path)
    monkeypatch.setattr(extractor, "_data_root", lambda persona_id: tmp_path)

    extracted = extractor.extract_persona_data("p05")
    scenario_prompt = scenario_gen._build_prompt(extracted)
    action_prompt = action_planner._build_prompt(
        {
            "id": "scen_test",
            "title": "Freelance Stabilization",
            "horizon": "1yr",
            "likelihood": "most_likely",
            "summary": "Theo stabilizes freelance income by tightening follow-through and cash collection.",
        },
        extracted,
    )

    assert "Open pipeline value" in scenario_prompt
    assert "Due-soon lead follow-ups" in scenario_prompt
    assert "High-pressure budget commitments" in scenario_prompt
    assert "Top monetization leads" in action_prompt
    assert "Due-soon time commitments" in action_prompt
    assert "nl_novabit" in action_prompt
    assert "tc_followup_block" in action_prompt
    assert "bc_invoice_gap" in action_prompt


@pytest.mark.fast
@pytest.mark.asyncio
async def test_analysis_cache_treats_notion_leads_as_scenario_relevant(tmp_path, monkeypatch):
    _seed_persona_dir(tmp_path)
    monkeypatch.setattr(extractor, "_data_root", lambda persona_id: tmp_path)
    cache = AnalysisCache(data_dir=tmp_path, persona_id="p05")

    call_count = 0

    async def _fake_run_scenario_llm(extracted, persona_id, has_llm, kg_snippets):  # noqa: ANN001
        nonlocal call_count
        call_count += 1
        return [
            {
                "id": "scen_test",
                "title": f"Scenario {call_count}",
                "summary": "summary",
                "horizon": "1yr",
                "likelihood": "possible",
                "tags": [],
                "pattern_ids": [],
            }
        ]

    async def _fake_fetch_kg_snippets(self, has_llm):  # noqa: ANN001
        return []

    monkeypatch.setattr("daemon.analysis_cache._run_scenario_llm", _fake_run_scenario_llm)
    monkeypatch.setattr(AnalysisCache, "_fetch_kg_snippets", _fake_fetch_kg_snippets)

    first, regenerated_first = await cache.get_scenarios(changed_domains={"notion_leads"}, has_llm=True)
    second, regenerated_second = await cache.get_scenarios(changed_domains={"notion_leads"}, has_llm=True)

    _write_jsonl(
        tmp_path / "notion_leads.jsonl",
        [
            {
                "id": "nl_novabit",
                "ts": "2026-03-12",
                "text": "NovaBit [Proposal sent] High priority, $3200. Next action: Send final proposal. Follow up by 2026-03-12.",
                "tags": ["notion", "lead", "proposal sent", "high", "pipeline"],
                "source": "notion",
                "origin": "live_webhook",
                "run_id": "run_2",
                "external_url": "https://www.notion.so/page1",
                "notion_page_id": "page1",
                "lead_key": "novabit::direct",
                "name": "NovaBit",
                "status": "Proposal sent",
                "priority": "High",
                "deal_size": 3200,
                "next_action": "Send final proposal",
                "next_follow_up_date": "2026-03-12",
                "win_probability": 0.7,
                "trust_risk": 0.15,
                "lane": "pipeline",
            }
        ],
    )

    third, regenerated_third = await cache.get_scenarios(changed_domains={"notion_leads"}, has_llm=True)

    assert regenerated_first is True
    assert regenerated_second is False
    assert regenerated_third is True
    assert first[0]["title"] == "Scenario 1"
    assert second[0]["title"] == "Scenario 1"
    assert third[0]["title"] == "Scenario 2"
