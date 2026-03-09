"""GET /v1/patterns — List patterns for a persona."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.auth import get_livemode

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class Pattern(BaseModel):
    id: str
    trend: str                    # "upward" | "downward" | "stable" | "cyclical"
    domains: list[str]            # e.g. ["financial", "calendar"]
    confidence: float             # 0.0–1.0
    data_refs: list[str]          # specific record IDs or descriptions
    is_cross_domain: bool
    title: str                    # short human label e.g. "Burnout Cascade"
    evidence_summary: str         # 1–2 sentence narrative


class PatternListResponse(BaseModel):
    object: str = "list"
    data: list[Pattern]
    has_more: bool = False
    url: str = "/v1/patterns"


# ---------------------------------------------------------------------------
# Demo fallback data
# ---------------------------------------------------------------------------

DEMO_PATTERNS_P05: list[Pattern] = [
    Pattern(
        id="p_burnout_cascade",
        trend="cyclical",
        domains=["financial", "calendar", "lifelog"],
        confidence=0.87,
        data_refs=["calendar_2026-02-10_week", "transactions_2026-02-14", "lifelog_2026-02-15"],
        is_cross_domain=True,
        title="Burnout Cascade",
        evidence_summary="After weeks with 30+ hours of meetings, Theo's exercise drops and delivery food spending triples. Financial, physical, and calendar domains all linked — breaking this cycle is the highest-leverage intervention.",
    ),
    Pattern(
        id="p_undercharge_cycle",
        trend="stable",
        domains=["financial"],
        confidence=0.91,
        data_refs=["transactions_2026-01-15", "transactions_2026-02-03", "transactions_2026-02-20"],
        is_cross_domain=False,
        title="Chronic Undercharging",
        evidence_summary="7 of the last 9 client invoices were below Theo's stated rate floor. Average project billed at $640 against a $1,200 target — a $560 gap per project.",
    ),
    Pattern(
        id="p_focus_location",
        trend="stable",
        domains=["calendar", "lifelog"],
        confidence=0.79,
        data_refs=["calendar_2026-01-21", "lifelog_2026-01-21", "calendar_2026-02-04"],
        is_cross_domain=True,
        title="Location-Dependent Focus",
        evidence_summary="Theo completes 3x more deep work tasks on days he works from the UT library vs. home. Tuesday and Thursday afternoons show the highest focus scores.",
    ),
    Pattern(
        id="p_debt_trajectory",
        trend="downward",
        domains=["financial"],
        confidence=0.95,
        data_refs=["transactions_2026-01-01", "transactions_2026-02-01", "transactions_2026-03-01"],
        is_cross_domain=False,
        title="Credit Card Debt Creeping Up",
        evidence_summary="Outstanding balance grew from $4,200 to $5,840 over 90 days. Minimum payments are keeping pace but the principal is not shrinking — current trajectory adds $650/month.",
    ),
    Pattern(
        id="p_rate_raise_success",
        trend="upward",
        domains=["financial", "social"],
        confidence=0.83,
        data_refs=["transactions_2026-02-22", "social_posts_2026-02-18"],
        is_cross_domain=True,
        title="Public Work Drives Rate Increases",
        evidence_summary="The two highest-value invoices ($1,800 and $2,200) followed within 3 weeks of portfolio posts gaining 200+ engagements. Social visibility is directly converting to premium clients.",
    ),
]


# ---------------------------------------------------------------------------
# Helper: try to pull live patterns from analysis cache
# ---------------------------------------------------------------------------


def _patterns_from_cache(persona_id: str) -> list[Pattern] | None:
    """Try to get patterns from the analysis cache. Returns None if unavailable."""
    try:
        from daemon.analysis_cache import get_analysis_cache

        cache = get_analysis_cache()
        if cache is None:
            return None

        raw_patterns: list[dict[str, Any]] | None = getattr(cache, "_pattern_report", None)
        if not raw_patterns:
            # Try alternate attribute names the cache might use
            for attr in ("pattern_report", "patterns", "_patterns"):
                raw_patterns = getattr(cache, attr, None)
                if raw_patterns:
                    break

        if not raw_patterns:
            return None

        patterns: list[Pattern] = []
        for p in raw_patterns:
            try:
                patterns.append(
                    Pattern(
                        id=p.get("id", ""),
                        trend=p.get("trend", "stable"),
                        domains=p.get("domains", []),
                        confidence=float(p.get("confidence", 0.5)),
                        data_refs=p.get("data_refs", []),
                        is_cross_domain=bool(p.get("is_cross_domain", False)),
                        title=p.get("title", p.get("trend", "Pattern")),
                        evidence_summary=p.get("evidence_summary", p.get("summary", "")),
                    )
                )
            except Exception as e:
                logger.debug("Skipping malformed pattern entry: %s", e)

        return patterns if patterns else None
    except Exception as e:
        logger.debug("Could not read patterns from analysis cache: %s", e)
        return None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/patterns")
async def list_patterns(
    request: Request,
    persona_id: str = Query("p05"),
    limit: int = Query(20, ge=1, le=100),
    starting_after: str | None = Query(None),
):
    livemode = get_livemode(request.headers.get("Authorization"))

    # Try live cache first; fall back to demo data
    patterns = _patterns_from_cache(persona_id)
    if not patterns:
        if persona_id == "p05":
            patterns = DEMO_PATTERNS_P05
        else:
            patterns = []

    # Cursor-based pagination
    if starting_after:
        idx = next((i for i, p in enumerate(patterns) if p.id == starting_after), -1)
        if idx >= 0:
            patterns = patterns[idx + 1:]

    page = patterns[:limit]
    has_more = len(patterns) > limit

    return PatternListResponse(
        data=page,
        has_more=has_more,
        url="/v1/patterns",
    ).model_dump(mode="json")
