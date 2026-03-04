"""GET /v1/workers — Worker management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.api.v1.schemas import ListObject, generate_id, epoch_now, paginate
from app.deps import get_master
from app.middleware.errors import ApiException
from deepagent.loop import AlwaysOnMaster
from deepagent.skills.registry import SKILL_REGISTRY

router = APIRouter()


def _worker_resource(w: dict, livemode: bool = True) -> dict:
    wid = w.get("worker_id", "")
    if not wid.startswith("wrkr_"):
        wid = f"wrkr_{wid}"
    return {
        "id": wid,
        "object": "worker",
        "created": epoch_now(),
        "livemode": livemode,
        "metadata": {},
        "label": w.get("label", ""),
        "status": w.get("status", "ready"),
        "queue_depth": w.get("queue_depth", 0),
        "last_error": w.get("last_error"),
    }


@router.get("/workers")
async def list_workers(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    starting_after: str | None = Query(None),
    expand: list[str] | None = Query(None, alias="expand[]"),
    master: AlwaysOnMaster = Depends(get_master),
):
    state = await master.get_state()
    livemode = not request.headers.get("authorization", "").startswith("Bearer sk_test_")

    resources = [_worker_resource(w, livemode) for w in state.get("workers", [])]

    # Expand skills inline if requested
    expansions = set(expand) if expand else set()
    if "skills" in expansions:
        skills_by_worker = {}
        for skill in SKILL_REGISTRY:
            sd = skill.model_dump(mode="json")
            key = sd.get("worker_id", "")
            skills_by_worker.setdefault(key, []).append(sd)
        for r in resources:
            raw_id = r["id"].removeprefix("wrkr_")
            r["skills"] = skills_by_worker.get(raw_id, [])

    page, has_more = paginate(resources, limit=limit, starting_after=starting_after)
    return ListObject(data=page, has_more=has_more, url="/v1/workers").model_dump(mode="json")


@router.get("/workers/map")
async def get_worker_map(master: AlwaysOnMaster = Depends(get_master)):
    return await master.get_map()


@router.get("/workers/skills")
async def get_worker_skills():
    return {"object": "list", "data": [s.model_dump(mode="json") for s in SKILL_REGISTRY]}


@router.get("/workers/{worker_id}")
async def get_worker(
    worker_id: str,
    expand: list[str] | None = Query(None, alias="expand[]"),
    master: AlwaysOnMaster = Depends(get_master),
):
    state = await master.get_state()
    raw_id = worker_id.removeprefix("wrkr_")
    w = next((w for w in state.get("workers", []) if w.get("worker_id") == raw_id), None)
    if w is None:
        raise ApiException(status_code=404, code="resource_missing", message="Worker not found.", param="worker_id")

    resource = _worker_resource(w)
    expansions = set(expand) if expand else set()
    if "skills" in expansions:
        resource["skills"] = [
            s.model_dump(mode="json") for s in SKILL_REGISTRY
            if getattr(s, "worker_id", "") == raw_id
        ]

    return resource
