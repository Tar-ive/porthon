"""Shared schemas for V1 API — Stripe-like resource conventions."""

from __future__ import annotations

import time
from typing import Any, Generic, TypeVar

from ulid import ULID
from pydantic import BaseModel, Field

T = TypeVar("T")


def generate_id(prefix: str) -> str:
    """Generate a prefixed ULID: ``scen_01j5...``."""
    return f"{prefix}{str(ULID()).lower()}"


def epoch_now() -> int:
    return int(time.time())


# ---------------------------------------------------------------------------
# Base resource mixin
# ---------------------------------------------------------------------------


class BaseResource(BaseModel):
    id: str
    object: str
    created: int = Field(default_factory=epoch_now)
    livemode: bool = True
    metadata: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# List wrapper
# ---------------------------------------------------------------------------


class ListObject(BaseModel, Generic[T]):
    object: str = "list"
    data: list[T]
    has_more: bool = False
    url: str = ""


# ---------------------------------------------------------------------------
# Structured error
# ---------------------------------------------------------------------------


class ApiErrorBody(BaseModel):
    type: str = "invalid_request_error"
    code: str = "unknown"
    message: str = ""
    param: str | None = None
    doc_url: str | None = None


class ApiErrorResponse(BaseModel):
    error: ApiErrorBody


# ---------------------------------------------------------------------------
# Expansion helper
# ---------------------------------------------------------------------------


def parse_expand(expand: list[str] | None) -> set[str]:
    """Return a set of dot-notation expansion paths."""
    return set(expand) if expand else set()


# ---------------------------------------------------------------------------
# Pagination helper
# ---------------------------------------------------------------------------


def paginate(
    items: list[Any],
    limit: int = 20,
    starting_after: str | None = None,
) -> tuple[list[Any], bool]:
    """Return (page, has_more) using cursor-based pagination."""
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(100, limit))
    if starting_after:
        idx = next((i for i, item in enumerate(items) if getattr(item, "id", None) == starting_after or (isinstance(item, dict) and item.get("id") == starting_after)), -1)
        if idx >= 0:
            items = items[idx + 1 :]
    page = items[:limit]
    has_more = len(items) > limit
    return page, has_more
