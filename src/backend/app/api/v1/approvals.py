"""GET/POST /v1/approvals — Approval management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.api.v1.schemas import ListObject, epoch_now, paginate
from app.auth import get_livemode
from app.deps import get_master
from app.middleware.errors import ApiException
from deepagent.loop import AlwaysOnMaster

router = APIRouter()


class ResolveApprovalRequest(BaseModel):
    decision: str  # "approved" or "rejected"


def _approval_resource(a: dict, livemode: bool = True) -> dict:
    """Build approval resource. Ensure apprv_ prefix is always present (migration for stale IDs)."""
    approval_id = a.get("approval_id", "")
    if approval_id and not approval_id.startswith("apprv_"):
        approval_id = f"apprv_{approval_id}"
    return {
        "id": approval_id,
        "object": "approval",
        "created": a.get("created", epoch_now()),
        "livemode": livemode,
        "metadata": a.get("metadata", {}),
        "task_id": a.get("task_id", ""),
        "worker_id": a.get("worker_id", ""),
        "reason": a.get("reason", ""),
        "payload": a.get("payload", {}),
        "decision": a.get("decision"),
        "resolved_at": a.get("resolved_at"),
    }


def _normalize_approval_id(approval_id: str) -> str:
    """Normalize approval ID for state lookup - handles both old (no prefix) and new (with prefix) IDs."""
    return approval_id


def _find_approval(approvals: list, approval_id: str) -> dict | None:
    """Find approval by ID, handling both prefixed and non-prefixed IDs."""
    # First try exact match
    for a in approvals:
        if a.get("approval_id") == approval_id:
            return a

    # Try stripped prefix
    if approval_id.startswith("apprv_"):
        stripped = approval_id[6:]
        for a in approvals:
            if a.get("approval_id") == stripped:
                return a

    # Try with prefix added
    if not approval_id.startswith("apprv_"):
        prefixed = f"apprv_{approval_id}"
        for a in approvals:
            if a.get("approval_id") == prefixed:
                return a

    return None


@router.get("/approvals")
async def list_approvals(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    starting_after: str | None = Query(None),
    pending: bool = Query(
        False, description="If true, only return unresolved approvals"
    ),
    master: AlwaysOnMaster = Depends(get_master),
):
    state = await master.get_state()
    livemode = get_livemode(request.headers.get("Authorization"))

    approvals = state.get("approvals", [])
    if pending:
        approvals = [a for a in approvals if a.get("decision") is None]

    resources = [_approval_resource(a, livemode) for a in approvals]
    page, has_more = paginate(resources, limit=limit, starting_after=starting_after)
    return ListObject(data=page, has_more=has_more, url="/v1/approvals").model_dump(
        mode="json"
    )


@router.get("/approvals/{approval_id}")
async def get_approval(
    approval_id: str,
    request: Request,
    master: AlwaysOnMaster = Depends(get_master),
):
    state = await master.get_state()
    livemode = get_livemode(request.headers.get("Authorization"))

    a = _find_approval(state.get("approvals", []), approval_id)
    if a is None:
        raise ApiException(
            status_code=404,
            code="resource_missing",
            message="Approval not found.",
            param="approval_id",
        )

    return _approval_resource(a, livemode)


@router.post("/approvals/{approval_id}/resolve")
async def resolve_approval(
    approval_id: str,
    body: ResolveApprovalRequest,
    master: AlwaysOnMaster = Depends(get_master),
):
    # Find the approval first to get the correct ID format from state
    state = await master.get_state()
    a = _find_approval(state.get("approvals", []), approval_id)
    if a is None:
        raise ApiException(
            status_code=404,
            code="resource_missing",
            message="Approval not found.",
            param="approval_id",
        )

    # Use the ID as stored in state
    state_approval_id = a.get("approval_id", approval_id)
    result = await master.resolve_approval(state_approval_id, body.decision)
    if not result.get("ok"):
        err = result.get("error", "Unknown error")
        raise ApiException(
            status_code=404 if "not found" in err else 400,
            code="resource_missing" if "not found" in err else "invalid_request",
            message=err,
            param="approval_id",
        )

    return {
        "id": approval_id,
        "object": "approval",
        "decision": result.get("decision"),
        "cycle": result.get("cycle"),
    }
