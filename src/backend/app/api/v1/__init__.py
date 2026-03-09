"""V1 API — Stripe-like conventions."""

from fastapi import APIRouter, Depends
from app.auth import swagger_auth

from .health import router as health_router
from .scenarios import router as scenarios_router
from .quests import router as quests_router
from .actions import router as actions_router
from .approvals import router as approvals_router
from .events import router as events_router
from .workers import router as workers_router
from .messages import router as messages_router
from .runtime import router as runtime_router
from .integrations import router as integrations_router
from .figma import router as figma_router
from .notion_leads import router as notion_leads_router
from .notion_webhooks import router as notion_webhooks_router
from .knowledge_graph import router as knowledge_graph_router
from .patterns import router as patterns_router
from .voice import router as voice_router

router = APIRouter(prefix="/v1", tags=["v1"], dependencies=[Depends(swagger_auth)])
router.include_router(health_router)
router.include_router(patterns_router)
router.include_router(scenarios_router)
router.include_router(quests_router)
router.include_router(actions_router)
router.include_router(approvals_router)
router.include_router(events_router)
router.include_router(workers_router)
router.include_router(messages_router)
router.include_router(runtime_router)
router.include_router(integrations_router)
router.include_router(figma_router)
router.include_router(notion_leads_router)
router.include_router(notion_webhooks_router)
router.include_router(knowledge_graph_router)
router.include_router(voice_router)
