import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.intent import classify_intent
from agent.prompt_builder import build_system_prompt
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
    if os.environ.get("NEO4J_URI"):
        try:
            from agent.retriever import create_rag_instance

            _rag = create_rag_instance()
            logger.info("LightRAG initialized with Neo4j + Qdrant")
        except Exception as e:
            logger.warning(f"LightRAG init failed (running without KG): {e}")
            _rag = None
    else:
        logger.info("NEO4J_URI not set — running without knowledge graph")
    yield
    _rag = None


app = FastAPI(lifespan=lifespan)


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


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "backend": "openai" if USE_OPENAI else "ollama",
        "rag": _rag is not None,
    }


@app.get("/api/scenarios")
async def get_scenarios():
    try:
        extracted = extract_persona_data("p05")
        scenarios = await asyncio.wait_for(generate_scenarios_llm(extracted), timeout=30.0)
        return scenarios
    except asyncio.TimeoutError:
        return generate_scenarios_fallback()
    except Exception as e:
        logger.error(f"Scenario generation failed: {e}")
        return generate_scenarios_fallback()


class ActionRequest(BaseModel):
    scenario_id: str
    scenario_title: str
    scenario_summary: str
    scenario_horizon: str
    scenario_likelihood: str


@app.post("/api/actions")
async def get_actions(request: ActionRequest):
    try:
        extracted = extract_persona_data("p05")
        scenario = {
            "id": request.scenario_id,
            "title": request.scenario_title,
            "summary": request.scenario_summary,
            "horizon": request.scenario_horizon,
            "likelihood": request.scenario_likelihood,
        }
        actions = await asyncio.wait_for(generate_actions(scenario, extracted), timeout=30.0)
        return actions
    except asyncio.TimeoutError:
        return {"scenario_id": request.scenario_id, "actions": [], "error": "timeout"}
    except Exception as e:
        logger.error(f"Action planning failed: {e}")
        return {"scenario_id": request.scenario_id, "actions": [], "error": str(e)}


@app.post("/api/chat")
async def handle_chat(request: ChatRequest):
    # Extract last user message for intent classification
    last_user_text = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            last_user_text = extract_text(msg)
            break

    # Classify intent and optionally retrieve KG context
    intent = classify_intent(last_user_text) if last_user_text else "casual"
    context = None

    if _rag is not None:
        try:
            from agent.retriever import retrieve_context

            context, intent = await retrieve_context(last_user_text, _rag)
        except Exception as e:
            logger.error(f"RAG retrieval error: {e}")

    # Build scenario context string if a scenario was selected
    scenario_context = None
    if request.scenario:
        scenario_context = (
            f"The user is exploring the '{request.scenario.title}' scenario "
            f"({request.scenario.horizon}, {request.scenario.likelihood}): "
            f"{request.scenario.summary}"
        )

    # Build system prompt from SOUL + USER + context
    system_prompt = build_system_prompt(context=context, intent=intent, scenario=scenario_context)

    events = (
        iter_openai_events(request.messages, model=OPENAI_MODEL, system_prompt=system_prompt)
        if USE_OPENAI
        else iter_ollama_events(
            request.messages, host=OLLAMA_HOST, model=OLLAMA_MODEL, system_prompt=system_prompt
        )
    )
    response = StreamingResponse(wrap_stream(events), media_type="text/event-stream")
    response.headers["x-porthon-intent"] = intent
    return patch_response_with_headers(response)


# Serve the Vite SPA — html=True handles client-side routing (returns index.html for unknown paths)
if ASSETS_DIR.exists():
    app.mount("/", StaticFiles(directory=ASSETS_DIR, html=True), name="spa")
