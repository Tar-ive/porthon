"""POST/GET /v1/quests — Quest lifecycle (merged quest + activate)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.api.v1.schemas import ListObject, generate_id, epoch_now, paginate, parse_expand
from app.deps import get_master
from app.middleware.errors import ApiException
from deepagent.loop import AlwaysOnMaster
from state.models import TaskStatus

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateQuestRequest(BaseModel):
    scenario_id: str
    persona_id: str = "p05"


def _quest_resource(master_result: dict[str, Any], scenario_id: str, persona_id: str, livemode: bool) -> dict[str, Any]:
    active = master_result.get("active_scenario", {})
    state = master_result.get("cycle", {})
    seeded = master_result.get("seeded_tasks", 0)

    quest_id = generate_id("qst_")
    return {
        "id": quest_id,
        "object": "quest",
        "created": epoch_now(),
        "livemode": livemode,
        "metadata": {},
        "scenario": scenario_id,
        "persona_id": persona_id,
        "status": "active",
        "seeded_tasks": seeded,
        "cycle": state,
        "tasks": master_result.get("cycle", {}).get("executed_tasks", []) + master_result.get("cycle", {}).get("approval_waiting", []),
    }


@router.post("/quests")
async def create_quest(
    body: CreateQuestRequest,
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
):
    from pipeline.extractor import extract_persona_data
    from pipeline.scenario_gen import generate_scenarios as generate_scenarios_llm
    from pipeline.action_planner import generate_actions

    livemode = not request.headers.get("authorization", "").startswith("Bearer sk_test_")

    try:
        extracted = extract_persona_data(body.persona_id)
        scenarios = await asyncio.wait_for(generate_scenarios_llm(extracted), timeout=30.0)
        chosen = next(
            (s for s in scenarios if s.get("id") == body.scenario_id),
            scenarios[0] if scenarios else {"id": body.scenario_id, "title": "Quest", "summary": ""},
        )
        await asyncio.wait_for(generate_actions(chosen, extracted), timeout=30.0)
        result = await master.activate_scenario(scenario=chosen)
    except asyncio.TimeoutError:
        raise ApiException(status_code=504, code="timeout", message="Quest activation timed out.")
    except Exception as e:
        logger.error(f"Quest activation failed: {e}")
        raise ApiException(status_code=500, code="internal_error", message=str(e))

    return _quest_resource(result, body.scenario_id, body.persona_id, livemode)


@router.get("/quests")
async def list_quests(
    request: Request,
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    starting_after: str | None = Query(None),
    expand: list[str] | None = Query(None, alias="expand[]"),
    master: AlwaysOnMaster = Depends(get_master),
):
    # Current architecture has at most one active quest (the active scenario).
    state = await master.get_state()
    quests = []
    if state.get("active_scenario"):
        sc = state["active_scenario"]
        quests.append({
            "id": generate_id("qst_"),
            "object": "quest",
            "created": epoch_now(),
            "livemode": True,
            "metadata": {},
            "scenario": sc.get("scenario_id", ""),
            "persona_id": state.get("persona_id", "p05"),
            "status": "active",
            "seeded_tasks": len([t for t in state.get("queue", []) if True]),
            "tasks": [t.get("task_id", "") for t in state.get("queue", [])],
        })

    page, has_more = paginate(quests, limit=limit, starting_after=starting_after)
    return ListObject(data=page, has_more=has_more, url="/v1/quests").model_dump(mode="json")


@router.get("/quests/{quest_id}")
async def get_quest(
    quest_id: str,
    expand: list[str] | None = Query(None, alias="expand[]"),
    master: AlwaysOnMaster = Depends(get_master),
):
    # Stub — would need persistent quest store for full implementation
    raise ApiException(status_code=404, code="resource_missing", message="Quest not found.", param="quest_id")
