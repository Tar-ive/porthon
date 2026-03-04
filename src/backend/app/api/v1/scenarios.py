"""GET /v1/scenarios — List & retrieve scenarios."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Any

from fastapi import APIRouter, Query, Request

from app.api.v1.schemas import ListObject, epoch_now, paginate
from app.auth import get_livemode
from app.middleware.errors import ApiException

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory cache: maps pipeline raw id → stable scen_ resource.
# Survives across requests within the same server process.
_scenario_cache: dict[str, dict[str, Any]] = {}

# Cache for generated scenarios with TTL (60 seconds)
_scenarios_generated_at: float = 0
_SCENARIOS_CACHE_TTL: float = 60.0  # seconds


def _stable_scen_id(raw_id: str) -> str:
    """Deterministic scen_ ID from pipeline ID so it's stable across calls."""
    h = hashlib.sha256(raw_id.encode()).hexdigest()[:20]
    return f"scen_{h}"


def _to_resource(raw: dict[str, Any], livemode: bool = True) -> dict[str, Any]:
    """Convert a pipeline scenario dict into a Stripe-like resource."""
    raw_id = raw.get("id", "unknown")
    scen_id = _stable_scen_id(raw_id)
    resource = {
        "id": scen_id,
        "object": "scenario",
        "created": epoch_now(),
        "livemode": livemode,
        "metadata": {},
        "title": raw.get("title", ""),
        "horizon": raw.get("horizon", ""),
        "likelihood": raw.get("likelihood", ""),
        "summary": raw.get("summary", ""),
        "tags": raw.get("tags", []),
        "patterns": raw.get("pattern_ids", []),
        "_raw_id": raw_id,  # keep for quest activation
    }
    _scenario_cache[scen_id] = resource
    _scenario_cache[raw_id] = resource  # also index by raw ID
    return resource


# Cache for generated scenarios (raw data, before conversion to resources)
_cached_scenarios: list[dict] | None = None


async def _generate_scenarios(
    persona_id: str = "p05", use_cache: bool = True
) -> list[dict]:
    global _cached_scenarios, _scenarios_generated_at

    # Return cached if still valid
    if use_cache and _cached_scenarios is not None:
        now = time.monotonic()
        if now - _scenarios_generated_at < _SCENARIOS_CACHE_TTL:
            return _cached_scenarios

    from pipeline.extractor import extract_persona_data
    from pipeline.scenario_gen import generate_scenarios as generate_scenarios_llm
    from simulation.scenarios import generate_scenarios as generate_scenarios_fallback

    try:
        extracted = extract_persona_data(persona_id)
        scenarios = await asyncio.wait_for(
            generate_scenarios_llm(extracted), timeout=30.0
        )
    except asyncio.TimeoutError:
        scenarios = generate_scenarios_fallback()
    except Exception as e:
        logger.error(f"Scenario generation failed: {e}")
        scenarios = generate_scenarios_fallback()

    # Cache the result
    _cached_scenarios = scenarios
    _scenarios_generated_at = time.monotonic()

    return scenarios


@router.get("/scenarios")
async def list_scenarios(
    request: Request,
    persona_id: str = Query("p05"),
    limit: int = Query(20, ge=1, le=100),
    starting_after: str | None = Query(None),
    expand: list[str] | None = Query(None, alias="expand[]"),
):
    livemode = get_livemode(request.headers.get("Authorization"))
    scenarios_raw = await _generate_scenarios(persona_id)
    resources = [_to_resource(s, livemode=livemode) for s in scenarios_raw]

    # Strip internal field from response
    cleaned = [{k: v for k, v in r.items() if not k.startswith("_")} for r in resources]
    page, has_more = paginate(cleaned, limit=limit, starting_after=starting_after)

    return ListObject(
        data=page,
        has_more=has_more,
        url="/v1/scenarios",
    ).model_dump(mode="json")


@router.get("/scenarios/{scenario_id}")
async def get_scenario(
    request: Request,
    scenario_id: str,
    expand: list[str] | None = Query(None, alias="expand[]"),
):
    livemode = get_livemode(request.headers.get("Authorization"))

    # Check cache first
    if scenario_id in _scenario_cache:
        resource = {**_scenario_cache[scenario_id], "livemode": livemode}
        return {k: v for k, v in resource.items() if not k.startswith("_")}

    # Cache miss — regenerate and populate cache
    scenarios_raw = await _generate_scenarios()
    resources = [_to_resource(s, livemode=livemode) for s in scenarios_raw]
    match = next((r for r in resources if r["id"] == scenario_id), None)
    if match is None:
        raise ApiException(
            status_code=404,
            code="resource_missing",
            message="Scenario not found.",
            param="scenario_id",
        )
    return {k: v for k, v in match.items() if not k.startswith("_")}
