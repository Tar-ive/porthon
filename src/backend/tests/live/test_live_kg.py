"""Live KG integration tests (Neo4j + Qdrant + embedding/LLM backends)."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from dotenv import load_dotenv

# Load env from repo root for local runs.
_path = Path(__file__).resolve()
for parent in _path.parents:
    env_file = parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        break

pytestmark = pytest.mark.live

REQUIRED_ENV = {"NEO4J_URI", "LLM_BINDING_API_KEY", "EMBEDDING_BINDING_API_KEY"}


def _skip_reason() -> str | None:
    if os.environ.get("RUN_LIVE_TESTS") != "1":
        return "Live tests disabled. Set RUN_LIVE_TESTS=1."
    if os.environ.get("RUN_LIVE_KG_TESTS") != "1":
        return "KG live tests disabled. Set RUN_LIVE_KG_TESTS=1."

    missing = [key for key in REQUIRED_ENV if not os.environ.get(key)]
    if missing:
        return "KG live test missing required env vars: " + ", ".join(sorted(missing))
    return None


@pytest.mark.asyncio
async def test_live_kg_retrieval_roundtrip():
    reason = _skip_reason()
    if reason:
        pytest.skip(reason)

    from deepagent.workers.kg_worker import KgWorker, _create_rag_instance

    rag = _create_rag_instance()
    assert rag is not None, "LightRAG instance creation failed"
    await rag.initialize_storages()

    seed_id = f"kg-live-seed-{uuid4()}"
    seed_doc = (
        f"{seed_id}: Theo booked two focused design blocks this week and logged one lead follow-up."
    )
    await rag.ainsert(seed_doc)

    # Use the KG worker's search action
    worker = KgWorker()
    result = await worker.execute("search", {
        "query": f"What pattern does {seed_id} reveal about Theo's recent work and schedule?",
    })

    assert result.ok, f"KG search failed: {result.message}"
    assert result.data["intent"] in {"pattern", "factual", "advice", "reflection", "emotional", "casual"}
    context = result.data.get("raw_context", "")
    assert len(context.strip()) > 0, "KG returned empty context"
    assert seed_id in context, f"Seed ID not found in context: {context[:200]}"

