"""GET/POST /v1/approvals — Approval management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.api.v1.schemas import ListObject, generate_id, epoch_now, paginate
from app.deps import get_master
from app.middleware.errors import ApiException
from deepagent.loop import AlwaysOnMaster

router = APIRouter()


class ResolveApprovalRequest(BaseModel):
    decision: str  # "approved" or "rejected"


@router.get("/approvals")
async def list_approvals(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    starting_after: str | None = Query(None),
    master: AlwaysOnMaster = Depends(get_master),
):
    state = await master.get_state()
    livemode = not request.headers.get("authorization", "").startswith("Bearer sk_test_")

    resources = []
    for a in state.get("approvals", []):
        apprv_id = a.get("approval_id", "")
        if not apprv_id.startswith("apprv_"):
            apprv_id = f"apprv_{apprv_id}" if apprv_id else generate_id("apprv_")
        resources.append({
            "id": apprv_id,
            "object": "approval",
            "created": epoch_now(),
            "livemode": livemode,
            "metadata": {},
            "task_id": a.get("task_id", ""),
            "worker_id": a.get("worker_id", ""),
            "reason": a.get("reason", ""),
            "payload": a.get("payload", {}),
            "decision": a.get("decision"),
            "resolved_at": a.get("resolved_at"),
        })

    page, has_more = paginate(resources, limit=limit, starting_after=starting_after)
    return ListObject(data=page, has_more=has_more, url="/v1/approvals").model_dump(mode="json")


@router.get("/approvals/{approval_id}")
async def get_approval(
    approval_id: str,
    master: AlwaysOnMaster = Depends(get_master),
):
    state = await master.get_state()
    a = next((a for a in state.get("approvals", []) if a.get("approval_id") == approval_id), None)
    if a is None:
        raise ApiException(status_code=404, code="resource_missing", message="Approval not found.", param="approval_id")

    return {
        "id": approval_id,
        "object": "approval",
        "created": epoch_now(),
        "livemode": True,
        "metadata": {},
        "task_id": a.get("task_id", ""),
        "worker_id": a.get("worker_id", ""),
        "reason": a.get("reason", ""),
        "payload": a.get("payload", {}),
        "decision": a.get("decision"),
        "resolved_at": a.get("resolved_at"),
    }


@router.post("/approvals/{approval_id}/resolve")
async def resolve_approval(
    approval_id: str,
    body: ResolveApprovalRequest,
    master: AlwaysOnMaster = Depends(get_master),
):
    result = await master.resolve_approval(approval_id, body.decision)
    if not result.get("ok"):
        raise ApiException(
            status_code=404 if "not found" in result.get("error", "") else 400,
            code="resource_missing" if "not found" in result.get("error", "") else "invalid_request",
            message=result.get("error", "Unknown error"),
            param="approval_id",
        )

    return {
        "id": approval_id,
        "object": "approval",
        "decision": result.get("decision"),
        "cycle": result.get("cycle"),
    }
