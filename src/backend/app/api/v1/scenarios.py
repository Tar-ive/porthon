"""GET /v1/scenarios — List & retrieve scenarios."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Query, Request

from app.api.v1.schemas import ListObject, generate_id, epoch_now, paginate, parse_expand
from app.middleware.errors import ApiException

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_resource(raw: dict[str, Any], livemode: bool = True) -> dict[str, Any]:
    """Convert a pipeline scenario dict into a Stripe-like resource."""
    scen_id = raw.get("id", "")
    if not scen_id.startswith("scen_"):
        scen_id = generate_id("scen_")
    return {
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
    }


@router.get("/scenarios")
async def list_scenarios(
    request: Request,
    persona_id: str = Query("p05"),
    limit: int = Query(20, ge=1, le=100),
    starting_after: str | None = Query(None),
    expand: list[str] | None = Query(None, alias="expand[]"),
):
    from pipeline.extractor import extract_persona_data
    from pipeline.scenario_gen import generate_scenarios as generate_scenarios_llm
    from simulation.scenarios import generate_scenarios as generate_scenarios_fallback

    livemode = not request.headers.get("authorization", "").startswith("Bearer sk_test_")

    try:
        extracted = extract_persona_data(persona_id)
        scenarios_raw = await asyncio.wait_for(generate_scenarios_llm(extracted), timeout=30.0)
    except asyncio.TimeoutError:
        scenarios_raw = generate_scenarios_fallback()
    except Exception as e:
        logger.error(f"Scenario generation failed: {e}")
        scenarios_raw = generate_scenarios_fallback()

    resources = [_to_resource(s, livemode=livemode) for s in scenarios_raw]
    page, has_more = paginate(resources, limit=limit, starting_after=starting_after)

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
    # In the current architecture, scenarios are generated on-the-fly.
    # For a single-resource fetch we regenerate and find.
    from pipeline.extractor import extract_persona_data
    from pipeline.scenario_gen import generate_scenarios as generate_scenarios_llm
    from simulation.scenarios import generate_scenarios as generate_scenarios_fallback

    livemode = not request.headers.get("authorization", "").startswith("Bearer sk_test_")

    try:
        extracted = extract_persona_data("p05")
        scenarios_raw = await asyncio.wait_for(generate_scenarios_llm(extracted), timeout=30.0)
    except Exception:
        scenarios_raw = generate_scenarios_fallback()

    resources = [_to_resource(s, livemode=livemode) for s in scenarios_raw]
    match = next((s for s in resources if s["id"] == scenario_id), None)
    if match is None:
        raise ApiException(status_code=404, code="resource_missing", message="Scenario not found.", param="scenario_id")
    return match
