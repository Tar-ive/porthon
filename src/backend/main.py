import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.api.routes_agent import router as agent_router
from app.api.v1 import router as v1_router
from app.middleware.errors import (
    ApiException,
    api_exception_handler,
    generic_exception_handler,
)
from app.middleware.idempotency import IdempotencyMiddleware
from deepagent.workers.kg_worker import classify_intent, _create_rag_instance
from deepagent.persona.prompt_builder import build_system_prompt
from deepagent.contracts import ProfileScores, QuestContext, QuestMemory, PersonaConfig  # noqa: F401
from deepagent.factory import create_master
from pipeline.action_planner import generate_actions
from pipeline.extractor import extract_persona_data
from pipeline.scenario_gen import generate_scenarios as generate_scenarios_llm
from simulation.scenarios import generate_scenarios as generate_scenarios_fallback
from utils import (
    ClientMessage,
    ClientMessagePart,  # noqa: F401 — re-exported for Pydantic schema discovery
    extract_text,
    iter_ollama_events,
    iter_openai_events,
    patch_response_with_headers,
    wrap_stream,
)

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# Map LightRAG-style LLM env vars to OpenAI SDK env vars so the openai
# client picks up OpenRouter (or any OpenAI-compatible provider) automatically.
if not os.environ.get("OPENAI_API_KEY") and os.environ.get("LLM_BINDING_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.environ["LLM_BINDING_API_KEY"]
if not os.environ.get("OPENAI_BASE_URL") and os.environ.get("LLM_BINDING_HOST"):
    os.environ["OPENAI_BASE_URL"] = os.environ["LLM_BINDING_HOST"]

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).parent / "static"

OLLAMA_HOST = "http://192.168.1.26:11434"
OLLAMA_MODEL = "qwen3:8b"
OPENAI_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

USE_OPENAI = bool(os.environ.get("OPENAI_API_KEY"))

# RAG instance — initialized at startup only when KG env vars are set
_rag = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _rag
    master = create_master(
        state_path=Path(__file__).parent / "state" / "runtime_state.json",
        tick_seconds=int(os.environ.get("AGENT_TICK_SECONDS", "900")),
    )
    await master.start()
    app.state.always_on_master = master

    if os.environ.get("NEO4J_URI"):
        try:
            _rag = _create_rag_instance()
            if _rag is not None:
                await _rag.initialize_storages()
                logger.info("LightRAG initialized with Neo4j + Qdrant")
            else:
                logger.warning("LightRAG creation returned None — running without KG")
        except Exception as e:
            logger.warning(f"LightRAG init failed (running without KG): {e}")
            _rag = None
    else:
        logger.info("NEO4J_URI not set — running without knowledge graph")
    yield
    await master.stop()
    if _rag is not None:
        try:
            if hasattr(_rag, "close"):
                await _rag.close()
            logger.info("LightRAG instance closed")
        except Exception as e:
            logger.warning(f"Error closing LightRAG: {e}")
    _rag = None


app = FastAPI(lifespan=lifespan)
app.add_middleware(IdempotencyMiddleware)
app.add_exception_handler(ApiException, api_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
app.include_router(v1_router)
app.include_router(agent_router)


class ScenarioContext(BaseModel):
    id: str
    title: str
    horizon: str
    likelihood: str
    summary: str


class ChatRequest(BaseModel):
    messages: List[ClientMessage]
    scenario: ScenarioContext | None = None

    model_config = {"extra": "allow"}


@app.get("/api/health", include_in_schema=False)
async def api_health(request: Request):
    from app.api.v1.health import health as v1_health

    return await v1_health(request)


@app.get("/api/scenarios", include_in_schema=False)
async def api_scenarios(request: Request):
    from app.api.v1.scenarios import list_scenarios

    return await list_scenarios(request)


@app.post("/api/actions", include_in_schema=False)
async def api_actions(request: Request):
    from app.api.v1.actions import create_actions, CreateActionRequest

    body = await request.json()
    action_req = CreateActionRequest(**body)
    return await create_actions(action_req, request)


@app.post("/api/chat", include_in_schema=False)
async def api_chat(request: Request):
    from app.api.v1.messages import create_message, CreateMessageRequest

    body = await request.json()
    msg = CreateMessageRequest(**body)
    return await create_message(msg, request)


class QuestRequest(BaseModel):
    scenario_id: str
    persona_id: str = "p05"


# Default profile scores for Theo (demo) — in production, computed by profiler
_DEMO_PROFILE_SCORES = ProfileScores(
    execution=0.45,
    growth=0.65,
    self_awareness=0.70,
    financial_stress=0.75,
    adhd_indicator=0.80,
    archetype="emerging_talent",
    deltas={"public_private": 0.40},
)


@app.post("/api/quest", include_in_schema=False)
async def api_quest(request: Request):
    from app.api.v1.quests import create_quest, CreateQuestRequest

    body = await request.json()
    quest_req = CreateQuestRequest(**body)
    return await create_quest(quest_req, request)


# /api/quest/outcomes is now handled by per-worker verify actions
# The old OutcomeCollector endpoint has been removed.


# Serve the Vite SPA — html=True handles client-side routing (returns index.html for unknown paths)
if ASSETS_DIR.exists():
    app.mount("/", StaticFiles(directory=ASSETS_DIR, html=True), name="spa")
