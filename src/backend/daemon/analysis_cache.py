"""Incremental analysis cache — dependency-aware, skips LLM when inputs unchanged.

Dependency graph:
    files (mtime)
      transactions.jsonl  →  finance_extract
      calendar.jsonl      →  calendar_extract
      lifelog.jsonl       →  lifelog_extract
      social_posts.jsonl  →  social_extract  (no LLM dependency)
           ↓  hash(profile + finance + calendar + lifelog)
      scenarios_node      →  skip LLM if hash unchanged
           ↓  hash(scenario + data_refs)
      actions_node[id]    →  skip LLM if hash unchanged

Every LLM call avoided saves ~$0.001–0.003 and 5–15 seconds.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Domains whose changes can affect the scenario generation prompt
_SCENARIO_DOMAINS: frozenset[str] = frozenset({"finance", "calendar", "lifelog"})

# Domain name → JSONL filename
_DOMAIN_FILE: dict[str, str] = {
    "finance": "transactions.jsonl",
    "calendar": "calendar.jsonl",
    "lifelog": "lifelog.jsonl",
    "social": "social_posts.jsonl",
    "conversations": "conversations.jsonl",
}


# ---------------------------------------------------------------------------
# Internal data nodes
# ---------------------------------------------------------------------------

@dataclass
class _DomainSnapshot:
    summary: dict | list
    raw: list
    mtime: float


@dataclass
class _ScenariosNode:
    scenarios: list[dict]
    input_hash: str   # sha256 of scenario-prompt inputs when LLM was called


@dataclass
class _ActionsNode:
    actions: list[dict]
    input_hash: str   # sha256 of action-prompt inputs when LLM was called


# ---------------------------------------------------------------------------
# AnalysisCache
# ---------------------------------------------------------------------------

class AnalysisCache:
    """Per-persona incremental analysis cache.

    Usage
    -----
    cache = AnalysisCache(data_dir=..., persona_id="p05")

    # From DataWatcher (knows which domain changed):
    scenarios, regenerated = await cache.get_scenarios(changed_domains={"finance"})

    # From HTTP route (full freshness check):
    scenarios, regenerated = await cache.get_scenarios()

    # Actions:
    actions, regenerated = await cache.get_actions(scenario, changed_domains={"calendar"})
    """

    def __init__(self, data_dir: Path, persona_id: str = "p05") -> None:
        self._data_dir = data_dir
        self._persona_id = persona_id
        self._profile: dict = {}
        self._profile_mtime: float = 0.0
        self._domains: dict[str, _DomainSnapshot] = {}
        self._data_refs: dict[str, str] = {}
        self._scenarios: _ScenariosNode | None = None
        self._actions: dict[str, _ActionsNode] = {}
        self._lock = asyncio.Lock()

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def get_scenarios(
        self,
        changed_domains: set[str] | None = None,
        has_llm: bool = True,
    ) -> tuple[list[dict], bool]:
        """Return (scenarios, was_regenerated).

        Parameters
        ----------
        changed_domains:
            Set of domain names that changed (from DataWatcher). Pass None for a
            full mtime-based freshness check (used by HTTP routes).
        has_llm:
            Whether LLM keys are available. Falls back to demo scenarios if False.
        """
        async with self._lock:
            self._refresh_profile()

            stale = (
                changed_domains
                if changed_domains is not None
                else self._stale_domains()
            )

            for domain in stale:
                self._extract_domain(domain)
            if stale:
                self._rebuild_data_refs()

            # Fast path: no scenario-relevant domain changed and we have cached results
            if not (stale & _SCENARIO_DOMAINS) and self._scenarios is not None:
                return self._scenarios.scenarios, False

            # Content-hash check: even if a domain was re-extracted, the prompt
            # may be identical (e.g. new record outside the top-12 window)
            input_hash = self._hash_scenario_inputs()
            if self._scenarios is not None and self._scenarios.input_hash == input_hash:
                logger.debug("AnalysisCache: scenario inputs unchanged, skipping LLM")
                return self._scenarios.scenarios, False

            # LLM call required — enrich with KG context first (non-blocking)
            extracted = self._assemble_extracted()
            kg_snippets = await self._fetch_kg_snippets(has_llm)
            scenarios = await _run_scenario_llm(extracted, self._persona_id, has_llm, kg_snippets)
            self._scenarios = _ScenariosNode(scenarios=scenarios, input_hash=input_hash)
            logger.info(
                "AnalysisCache: scenarios regenerated (%d) for persona=%s",
                len(scenarios),
                self._persona_id,
            )
            return scenarios, True

    async def get_actions(
        self,
        scenario: dict,
        changed_domains: set[str] | None = None,
        has_llm: bool = True,
    ) -> tuple[list[dict], bool]:
        """Return (actions, was_regenerated)."""
        async with self._lock:
            self._refresh_profile()

            stale = (
                changed_domains
                if changed_domains is not None
                else self._stale_domains()
            )

            for domain in stale:
                self._extract_domain(domain)
            if stale:
                self._rebuild_data_refs()

            scenario_id = scenario.get("id", "")
            input_hash = self._hash_action_inputs(scenario)
            cached = self._actions.get(scenario_id)
            if cached is not None and cached.input_hash == input_hash:
                logger.debug("AnalysisCache: action inputs unchanged for %s, skipping LLM", scenario_id)
                return cached.actions, False

            extracted = self._assemble_extracted()
            kg_snippets = await self._fetch_kg_snippets(has_llm)
            result = await _run_actions_llm(scenario, extracted, has_llm, kg_snippets)
            actions = result.get("actions", [])
            self._actions[scenario_id] = _ActionsNode(actions=actions, input_hash=input_hash)
            logger.info(
                "AnalysisCache: actions regenerated (%d) for scenario=%s",
                len(actions),
                scenario_id,
            )
            return actions, True

    def invalidate(self) -> None:
        """Force full regeneration on next call (external cache bust)."""
        self._scenarios = None
        self._actions.clear()

    async def _fetch_kg_snippets(self, has_llm: bool) -> list[str]:
        """Retrieve cross-domain patterns from the KG. Fails silently."""
        try:
            from deepagent.workers.kg_worker import KgWorker
            kg = KgWorker()
            name = self._profile.get("name", "Theo")
            payload: dict = {"query": f"{name}'s behavioral patterns and life trajectory"}
            if not has_llm:
                payload["demo_mode"] = True
            result = await asyncio.wait_for(kg._search(payload), timeout=8.0)
            if result.ok and result.data:
                return result.data.get("snippets", [])
        except Exception as exc:
            logger.warning("AnalysisCache: KG fetch failed: %s", exc)
        return []

    # -----------------------------------------------------------------------
    # Domain extraction (sync — called inside async lock)
    # -----------------------------------------------------------------------

    def _stale_domains(self) -> set[str]:
        stale: set[str] = set()
        for domain, filename in _DOMAIN_FILE.items():
            path = self._data_dir / filename
            if not path.exists():
                continue
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            cached = self._domains.get(domain)
            if cached is None or cached.mtime != mtime:
                stale.add(domain)
        return stale

    def _refresh_profile(self) -> None:
        path = self._data_dir / "persona_profile.json"
        if not path.exists():
            return
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return
        if mtime == self._profile_mtime and self._profile:
            return
        from pipeline.extractor import extract_profile
        self._profile = extract_profile(self._persona_id)
        self._profile_mtime = mtime

    def _extract_domain(self, domain: str) -> None:
        filename = _DOMAIN_FILE.get(domain)
        if not filename:
            return
        path = self._data_dir / filename
        if not path.exists():
            return
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return

        if domain == "finance":
            from pipeline.extractor import extract_transactions
            summary, raw = extract_transactions(self._persona_id)
        elif domain == "calendar":
            from pipeline.extractor import extract_calendar_data
            summary, raw = extract_calendar_data(self._persona_id)
        elif domain == "lifelog":
            from pipeline.extractor import extract_lifelog
            summary, raw = extract_lifelog(self._persona_id)
        elif domain == "social":
            from pipeline.extractor import extract_social
            summary, raw = extract_social(self._persona_id)
        else:
            return

        self._domains[domain] = _DomainSnapshot(summary=summary, raw=raw, mtime=mtime)

    def _rebuild_data_refs(self) -> None:
        refs: dict[str, str] = {}
        for domain in ("calendar", "finance", "lifelog", "social"):
            snap = self._domains.get(domain)
            if snap:
                for r in snap.raw:
                    rid = r.get("id")
                    if rid:
                        refs[rid] = r.get("text", "")
        self._data_refs = refs

    def _assemble_extracted(self) -> dict:
        def _snap_summary(domain: str, default):
            snap = self._domains.get(domain)
            return snap.summary if snap else default

        return {
            "profile": self._profile,
            "transactions": _snap_summary("finance", {}),
            "calendar": _snap_summary("calendar", {}),
            "lifelog": _snap_summary("lifelog", {}),
            "social": _snap_summary("social", []),
            "data_refs": self._data_refs,
        }

    # -----------------------------------------------------------------------
    # Hashing — must mirror exactly what scenario_gen and action_planner use
    # -----------------------------------------------------------------------

    def _hash_scenario_inputs(self) -> str:
        """Hash the inputs consumed by scenario_gen._build_prompt."""
        fin = self._domains.get("finance")
        cal = self._domains.get("calendar")
        ll = self._domains.get("lifelog")
        payload = {
            "profile": self._profile,
            "transactions": fin.summary if fin else {},
            "calendar": cal.summary if cal else {},
            "lifelog": ll.summary if ll else {},
        }
        return _sha256(payload)

    def _hash_action_inputs(self, scenario: dict) -> str:
        """Hash the inputs consumed by action_planner._build_prompt."""
        ll = self._domains.get("lifelog")
        payload = {
            "scenario": scenario,
            "profile": self._profile,
            "data_refs": self._data_refs,
            "lifelog_recent": (ll.summary or {}).get("recent", []) if ll else [],
        }
        return _sha256(payload)


# ---------------------------------------------------------------------------
# LLM helpers (thin wrappers so they can be patched in tests)
# ---------------------------------------------------------------------------

async def _run_scenario_llm(
    extracted: dict, persona_id: str, has_llm: bool, kg_snippets: list | None = None
) -> list[dict]:
    if not has_llm:
        from pipeline.demo_theo import generate_demo_scenarios
        return generate_demo_scenarios(persona_id)
    from pipeline.scenario_gen import generate_scenarios
    return await generate_scenarios(extracted, kg_snippets=kg_snippets)


async def _run_actions_llm(
    scenario: dict, extracted: dict, has_llm: bool, kg_snippets: list | None = None
) -> dict:
    if not has_llm:
        from pipeline.demo_theo import generate_demo_actions
        return generate_demo_actions(scenario.get("id", ""), "p05")
    from pipeline.action_planner import generate_actions
    return await generate_actions(scenario, extracted, kg_snippets=kg_snippets)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()
    ).hexdigest()


# ---------------------------------------------------------------------------
# Module-level singleton — shared between DataWatcher and HTTP routes
# ---------------------------------------------------------------------------

_cache: AnalysisCache | None = None


def init_analysis_cache(data_dir: Path, persona_id: str = "p05") -> AnalysisCache:
    global _cache
    _cache = AnalysisCache(data_dir=data_dir, persona_id=persona_id)
    return _cache


def get_analysis_cache() -> AnalysisCache | None:
    return _cache
