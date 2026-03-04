"""POST/GET /v1/actions — Action planning."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.api.v1.schemas import ListObject, generate_id, epoch_now, paginate
from app.auth import get_livemode
from app.middleware.errors import ApiException

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateActionRequest(BaseModel):
    scenario_id: str


@router.post("/actions")
async def create_actions(
    body: CreateActionRequest,
    request: Request,
):
    from pipeline.extractor import extract_persona_data
    from pipeline.scenario_gen import generate_scenarios as generate_scenarios_llm
    from pipeline.action_planner import generate_actions

    livemode = get_livemode(request.headers.get("Authorization"))

    try:
        extracted = extract_persona_data("p05")
        scenarios = await asyncio.wait_for(
            generate_scenarios_llm(extracted), timeout=30.0
        )
        chosen = next(
            (s for s in scenarios if s.get("id") == body.scenario_id),
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
    for raw in actions:
        resources.append(
            {
                "id": generate_id("act_"),
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
