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
from deepagent.contracts import ProfileScores, QuestContext, QuestMemory, PersonaConfig  # noqa: F401
from deepagent.factory import create_master
from utils import (
    ClientMessage,
    ClientMessagePart,  # noqa: F401 — re-exported for Pydantic schema discovery
)

_main_path = Path(__file__).resolve()
_dotenv_candidates = [
    _main_path.parent / ".env",
    _main_path.parent.parent / ".env",
    _main_path.parent.parent.parent / ".env",
]
for _dotenv_path in _dotenv_candidates:
    if _dotenv_path.exists():
        load_dotenv(_dotenv_path)
        break
else:
    load_dotenv()

# Map LightRAG-style LLM env vars to OpenAI SDK env vars so the openai
# client picks up OpenRouter (or any OpenAI-compatible provider) automatically.
if not os.environ.get("OPENAI_API_KEY") and os.environ.get("LLM_BINDING_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.environ["LLM_BINDING_API_KEY"]
if not os.environ.get("OPENAI_BASE_URL") and os.environ.get("LLM_BINDING_HOST"):
    os.environ["OPENAI_BASE_URL"] = os.environ["LLM_BINDING_HOST"]

logger = logging.getLogger(__name__)

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(levelname)s: %(message)s",
    )

ASSETS_DIR = Path(__file__).parent / "static"

OLLAMA_HOST = "http://192.168.1.26:11434"
OLLAMA_MODEL = "qwen3:8b"
OPENAI_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

USE_OPENAI = bool(os.environ.get("OPENAI_API_KEY"))

# RAG instance — initialized lazily when explicitly needed by live routes.
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

    # Init AnalysisCache (shared singleton — used by both DataWatcher and HTTP routes)
    from daemon.analysis_cache import init_analysis_cache
    _data_dir = Path(__file__).parent.parent.parent / "data" / "all_personas" / "persona_p05"
    init_analysis_cache(data_dir=_data_dir, persona_id="p05")

    # Start DataWatcher — polls Theo's JSONL files and publishes SSE events on change
    from daemon.watcher import DataWatcher
    data_watcher = DataWatcher(
        master=master,
        data_dir=_data_dir,
        persona_id="p05",
        poll_interval=float(os.environ.get("DATA_WATCHER_INTERVAL", "3.0")),
    )
    master.set_data_watcher(data_watcher)
    await data_watcher.start()
    app.state.data_watcher = data_watcher

    logger.info("Skipping eager LightRAG startup; KG is lazy-initialized when needed")
    yield
    await data_watcher.stop()
    master.set_data_watcher(None)
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


@app.get("/api/patterns", include_in_schema=False)
async def api_patterns(request: Request):
    from app.api.v1.patterns import list_patterns

    return await list_patterns(request=request)


@app.get("/api/scenarios", include_in_schema=False)
async def api_scenarios(request: Request):
    from app.api.v1.scenarios import list_scenarios

    qp = request.query_params
    persona_id = qp.get("persona_id", "p05")
    starting_after = qp.get("starting_after")
    expand = qp.getlist("expand[]") if hasattr(qp, "getlist") else None

    try:
        limit = int(qp.get("limit", "20"))
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(100, limit))

    return await list_scenarios(
        request=request,
        persona_id=persona_id,
        limit=limit,
        starting_after=starting_after,
        expand=expand,
    )


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


@app.post("/", include_in_schema=False)
async def root_webhook_fallback(request: Request):
    """Fallback for providers misconfigured to POST at service root."""
    from app.deps import get_master
    from app.api.v1.notion_webhooks import notion_webhooks_verify

    return await notion_webhooks_verify(request, master=get_master(request))


@app.post("/notion/webhooks", include_in_schema=False)
async def notion_webhook_fallback(request: Request):
    """Non-versioned alias for Notion webhook verification."""
    from app.deps import get_master
    from app.api.v1.notion_webhooks import notion_webhooks_verify

    return await notion_webhooks_verify(request, master=get_master(request))


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
