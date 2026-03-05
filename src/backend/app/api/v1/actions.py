"""POST/GET /v1/actions — Action planning."""

from __future__ import annotations

import asyncio
import hashlib
import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.v1.schemas import ListObject, generate_id, epoch_now
from app.auth import get_livemode, get_mode, get_persona_id
from app.middleware.errors import ApiException

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateActionRequest(BaseModel):
    scenario_id: str


def _stable_action_id(scenario_raw_id: str, idx: int) -> str:
    h = hashlib.sha256(f"{scenario_raw_id}:{idx}".encode()).hexdigest()[:20]
    return f"act_{h}"


@router.post("/actions")
async def create_actions(
    body: CreateActionRequest,
    request: Request,
):
    livemode = get_livemode(request.headers.get("Authorization"))
    mode = get_mode(request.headers.get("Authorization"))
    persona_id = get_persona_id(request.headers.get("Authorization"))

    scenario_id = body.scenario_id
    try:
        from app.api.v1.scenarios import _scenario_cache

        if scenario_id in _scenario_cache:
            scenario_id = _scenario_cache[scenario_id].get("_raw_id", scenario_id)
    except Exception:
        pass

    try:
        if mode == "demo":
            from pipeline.demo_theo import (
                generate_demo_actions,
                generate_demo_scenarios,
                normalize_demo_scenario_id,
            )

            scenario_id = normalize_demo_scenario_id(scenario_id)

            scenarios = generate_demo_scenarios(persona_id)
            chosen = next((s for s in scenarios if s.get("id") == scenario_id), None)
            result = generate_demo_actions(
                chosen.get("id", scenario_id) if chosen else scenario_id,
                persona_id=persona_id,
            )
        else:
            from pipeline.extractor import extract_persona_data
            from pipeline.scenario_gen import generate_scenarios as generate_scenarios_llm
            from pipeline.action_planner import generate_actions

            extracted = extract_persona_data(persona_id)
            scenarios = await asyncio.wait_for(
                generate_scenarios_llm(extracted), timeout=30.0
            )
            chosen = next(
                (s for s in scenarios if s.get("id") == scenario_id),
                scenarios[0] if scenarios else None,
            )
            if chosen is None:
                raise ApiException(
                    status_code=404,
                    code="resource_missing",
                    message="Scenario not found.",
                    param="scenario_id",
                )

            result = await asyncio.wait_for(
                generate_actions(chosen, extracted), timeout=30.0
            )

        if chosen is None:
            raise ApiException(
                status_code=404,
                code="resource_missing",
                message="Scenario not found.",
                param="scenario_id",
            )
    except ApiException:
        raise
    except asyncio.TimeoutError:
        raise ApiException(
            status_code=504, code="timeout", message="Action planning timed out."
        )
    except Exception as e:
        logger.error(f"Action planning failed: {e}")
        raise ApiException(status_code=500, code="internal_error", message=str(e))

    # Wrap raw actions in Stripe-like resources
    actions = result.get("actions", []) if isinstance(result, dict) else []
    resources = []
    for idx, raw in enumerate(actions):
        resources.append(
            {
                "id": _stable_action_id(chosen.get("id", scenario_id), idx)
                if mode == "demo"
                else generate_id("act_"),
                "object": "action",
                "created": epoch_now(),
                "livemode": livemode,
                "metadata": {},
                "scenario": body.scenario_id,
                "title": raw.get("action", ""),
                "description": raw.get("action", ""),
                "data_ref": raw.get("data_ref", ""),
                "pattern_id": raw.get("pattern_id", ""),
                "rationale": raw.get("rationale", ""),
                "compound_summary": raw.get("compound_summary", ""),
            }
        )

    return ListObject(data=resources, has_more=False, url="/v1/actions").model_dump(
        mode="json"
    )
