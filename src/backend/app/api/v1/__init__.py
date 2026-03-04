"""V1 API — Stripe-like conventions."""

from fastapi import APIRouter

from .health import router as health_router
from .scenarios import router as scenarios_router
from .quests import router as quests_router
from .actions import router as actions_router
from .approvals import router as approvals_router
from .events import router as events_router
from .workers import router as workers_router
from .messages import router as messages_router
from .runtime import router as runtime_router

router = APIRouter(prefix="/v1", tags=["v1"])
router.include_router(health_router)
router.include_router(scenarios_router)
router.include_router(quests_router)
router.include_router(actions_router)
router.include_router(approvals_router)
router.include_router(events_router)
router.include_router(workers_router)
router.include_router(messages_router)
router.include_router(runtime_router)
