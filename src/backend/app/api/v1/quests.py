"""POST/GET /v1/quests — Quest lifecycle (merged quest + activate)."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.api.v1.schemas import ListObject, epoch_now, paginate
from app.auth import get_livemode
from app.deps import get_master
from app.middleware.errors import ApiException
from deepagent.loop import AlwaysOnMaster

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateQuestRequest(BaseModel):
    scenario_id: str
    persona_id: str = "p05"


def _stable_quest_id(scenario_id: str, persona_id: str) -> str:
    """Deterministic quest ID derived from scenario + persona so it's stable."""
    h = hashlib.sha256(f"{scenario_id}:{persona_id}".encode()).hexdigest()[:20]
    return f"qst_{h}"


def _build_quest(state: dict[str, Any], livemode: bool = True) -> dict[str, Any] | None:
    """Build a quest resource from current runtime state."""
    sc = state.get("active_scenario")
    if not sc:
        return None
    scenario_id = sc.get("scenario_id", "")
    persona_id = state.get("persona_id", "p05")
    return {
        "id": _stable_quest_id(scenario_id, persona_id),
        "object": "quest",
        "created": epoch_now(),
        "livemode": livemode,
        "metadata": {},
        "scenario": scenario_id,
        "persona_id": persona_id,
        "status": "active",
        "seeded_tasks": len(state.get("queue", [])),
        "tasks": [t.get("task_id", "") for t in state.get("queue", [])],
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

    livemode = get_livemode(request.headers.get("Authorization"))

    # Resolve scen_ prefixed ID back to raw pipeline ID if needed
    scenario_id = body.scenario_id
    try:
        from app.api.v1.scenarios import _scenario_cache

        if scenario_id in _scenario_cache:
            scenario_id = _scenario_cache[scenario_id].get("_raw_id", scenario_id)
    except Exception:
        pass

    try:
        extracted = extract_persona_data(body.persona_id)
        scenarios = await asyncio.wait_for(
            generate_scenarios_llm(extracted), timeout=30.0
        )
        chosen = next(
            (s for s in scenarios if s.get("id") == scenario_id),
            scenarios[0]
            if scenarios
            else {"id": scenario_id, "title": "Quest", "summary": ""},
        )
        await asyncio.wait_for(generate_actions(chosen, extracted), timeout=30.0)
        result = await master.activate_scenario(scenario=chosen)
    except asyncio.TimeoutError:
        raise ApiException(
            status_code=504, code="timeout", message="Quest activation timed out."
        )
    except Exception as e:
        logger.error(f"Quest activation failed: {e}")
        raise ApiException(status_code=500, code="internal_error", message=str(e))

    state = await master.get_state()
    quest = _build_quest(state, livemode)
    if quest:
        quest["cycle"] = result.get("cycle")
    return quest or {"error": "no active scenario"}


@router.get("/quests")
async def list_quests(
    request: Request,
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    starting_after: str | None = Query(None),
    expand: list[str] | None = Query(None, alias="expand[]"),
    master: AlwaysOnMaster = Depends(get_master),
):
    state = await master.get_state()
    livemode = get_livemode(request.headers.get("Authorization"))

    quests = []
    quest = _build_quest(state, livemode)
    if quest:
        quests.append(quest)

    page, has_more = paginate(quests, limit=limit, starting_after=starting_after)
    return ListObject(data=page, has_more=has_more, url="/v1/quests").model_dump(
        mode="json"
    )


@router.get("/quests/{quest_id}")
async def get_quest(
    quest_id: str,
    expand: list[str] | None = Query(None, alias="expand[]"),
    master: AlwaysOnMaster = Depends(get_master),
):
    state = await master.get_state()
    quest = _build_quest(state)
    if quest and quest["id"] == quest_id:
        return quest
    raise ApiException(
        status_code=404,
        code="resource_missing",
        message="Quest not found.",
        param="quest_id",
    )
