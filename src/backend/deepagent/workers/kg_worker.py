"""KG Search Worker — the brain of the deep-agent system.

Absorbs:
  - agent/retriever.py  → create_rag_instance(), retrieve_context()
  - agent/intent.py     → classify_intent(), INTENT_TO_MODE

This worker provides KG context to all other workers via the dispatcher.
It is the single entry point for all knowledge graph operations:
  - search: query the KG for context relevant to an action
  - classify: determine the intent of a user query
  - ingest: (future) add new data to the KG

Output contract (from SKILL.md):
  {snippets: [...], confidence: float, intent: str, refs: [...]}
"""

from __future__ import annotations

import logging
import os
from typing import Any

from deepagent.workers.base import BaseWorker, WorkerExecution

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent classification (absorbed from agent/intent.py)
# ---------------------------------------------------------------------------

FACTUAL_TRIGGERS = [
    "how much", "what did i spend", "last month", "how many", "when did",
    "total", "subscription", "revenue", "income", "expense", "payment",
    "transaction", "invoice", "client", "calendar", "event", "email",
    "how often", "amount", "cost", "price", "debt",
]

PATTERN_TRIGGERS = [
    "pattern", "notice", "trend", "always", "keep doing", "habit",
    "recurring", "usually", "tendency", "behavior", "consistent",
    "over time", "changed", "getting better", "getting worse",
]

ADVICE_TRIGGERS = [
    "should i", "what do you think", "is it worth", "would you",
    "recommend", "advice", "suggest", "help me decide", "what if",
    "how do i", "strategy", "plan", "approach",
]

REFLECTION_TRIGGERS = [
    "who am i", "how am i doing", "progress", "growth", "my strengths",
    "my weaknesses", "self", "identity", "goals", "where do i stand",
    "am i", "tell me about myself",
]

EMOTIONAL_TRIGGERS = [
    "overwhelmed", "stressed", "anxious", "scared", "frustrated",
    "exhausted", "burned out", "sad", "worried", "freaking out",
    "can't do this", "give up", "stuck", "lost", "confused",
    "happy", "excited", "proud", "grateful",
]

# Map intent → LightRAG query mode
INTENT_TO_MODE: dict[str, str | None] = {
    "factual": "mix",
    "pattern": "global",
    "advice": "hybrid",
    "reflection": "hybrid",
    "emotional": None,
    "casual": None,
}


def classify_intent(query: str) -> str:
    """Classify user query intent for KG retrieval routing.

    Returns one of: factual, pattern, advice, reflection, emotional, casual
    """
    q = query.lower().strip()
    if any(t in q for t in EMOTIONAL_TRIGGERS):
        return "emotional"
    if any(t in q for t in ADVICE_TRIGGERS):
        return "advice"
    if any(t in q for t in REFLECTION_TRIGGERS):
        return "reflection"
    if any(t in q for t in PATTERN_TRIGGERS):
        return "pattern"
    if any(t in q for t in FACTUAL_TRIGGERS):
        return "factual"
    return "casual"


# ---------------------------------------------------------------------------
# RAG instance management (absorbed from agent/retriever.py)
# ---------------------------------------------------------------------------

_rag_instance = None


def _create_rag_instance(working_dir: str | None = None):
    """Create or return the singleton LightRAG instance.

    Configured for Neo4j graph storage + Qdrant vector storage.
    All config comes from environment variables.
    """
    global _rag_instance
    if _rag_instance is not None:
        return _rag_instance

    # Require all three pillars: graph DB, LLM, and embedding keys.
    # A partial config (e.g. Neo4j set but no LLM key) is treated as unconfigured
    # so we degrade cleanly instead of reaching LightRAG internals.
    neo4j_uri = os.environ.get("NEO4J_URI")
    llm_key = os.environ.get("LLM_BINDING_API_KEY") or os.environ.get("OPENAI_API_KEY")
    embedding_key = os.environ.get("EMBEDDING_BINDING_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not (neo4j_uri and llm_key and embedding_key):
        missing = [k for k, v in [
            ("NEO4J_URI", neo4j_uri),
            ("LLM_BINDING_API_KEY/OPENAI_API_KEY", llm_key),
            ("EMBEDDING_BINDING_API_KEY/OPENAI_API_KEY", embedding_key),
        ] if not v]
        logger.warning("KG not fully configured (missing: %s) — returning empty context", ", ".join(missing))
        return None

    try:
        import numpy as np
        from lightrag import LightRAG, QueryParam  # noqa: F401
        from lightrag.utils import EmbeddingFunc
        from openai import AsyncOpenAI

        if working_dir is None:
            persona_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "persona"
            )
            working_dir = os.path.join(persona_dir, "rag_storage")

        os.makedirs(working_dir, exist_ok=True)

        embedding_dim = int(os.getenv("EMBEDDING_DIM", "3072"))
        embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
        llm_model = os.getenv("LLM_MODEL", "x-ai/grok-4.1-fast")
        llm_host = os.getenv("LLM_BINDING_HOST", "https://openrouter.ai/api/v1")
        llm_api_key = os.getenv("LLM_BINDING_API_KEY", "")
        embedding_host = os.getenv("EMBEDDING_BINDING_HOST", "https://api.openai.com/v1")
        embedding_api_key = os.getenv("EMBEDDING_BINDING_API_KEY", "")
        cosine_threshold = float(os.getenv("COSINE_THRESHOLD", "0.2"))

        llm_client = AsyncOpenAI(api_key=llm_api_key, base_url=llm_host)
        embedding_client = AsyncOpenAI(api_key=embedding_api_key, base_url=embedding_host)

        async def llm_func(prompt, system_prompt=None, history_messages=[], **kwargs):
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if history_messages:
                messages.extend(history_messages)
            messages.append({"role": "user", "content": prompt})
            response = await llm_client.chat.completions.create(
                model=llm_model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.2),
                max_tokens=kwargs.get("max_tokens", 2048),
            )
            return response.choices[0].message.content or ""

        async def embed_func(texts: list[str]) -> list[list[float]]:
            response = await embedding_client.embeddings.create(
                model=embedding_model,
                input=texts,
            )
            return np.array([item.embedding for item in response.data], dtype=float)

        embedding = EmbeddingFunc(
            embedding_dim=embedding_dim,
            max_token_size=8192,
            func=embed_func,
            model_name=embedding_model,
        )

        _rag_instance = LightRAG(
            working_dir=working_dir,
            llm_model_func=llm_func,
            llm_model_name=llm_model,
            embedding_func=embedding,
            graph_storage="Neo4JStorage",
            vector_storage="QdrantVectorDBStorage",
            vector_db_storage_cls_kwargs={
                "cosine_better_than_threshold": cosine_threshold,
            },
        )

        logger.info("KG worker: LightRAG instance created (Neo4j + Qdrant)")
        return _rag_instance

    except ImportError as e:
        logger.warning(f"KG worker: LightRAG dependency missing: {e}")
        return None
    except Exception as e:
        logger.error(f"KG worker: Failed to create RAG instance: {e}")
        return None


# ---------------------------------------------------------------------------
# KG Worker
# ---------------------------------------------------------------------------

class KgWorker(BaseWorker):
    """Knowledge Graph search worker.

    Provides context retrieval and intent classification for all other
    workers. The dispatcher runs this FIRST and injects the result as
    kg_context into every subsequent worker's payload.
    """

    worker_id = "kg_worker"
    label = "KG Search"

    ACTIONS = {
        "search": "_search",
        "classify": "_classify",
        "refresh_context": "_search",
        "retrieve_context": "_search",
    }

    async def execute(self, action: str, payload: dict) -> WorkerExecution:
        handler_name = self.ACTIONS.get(action)
        if not handler_name:
            return WorkerExecution(ok=False, message=f"Unknown KG action: {action}")

        if action in {"refresh_context", "retrieve_context"} and not payload.get("query"):
            payload = {
                **payload,
                "query": payload.get("scenario_summary")
                or payload.get("scenario_title")
                or "refresh scenario context",
            }

        handler = getattr(self, handler_name)
        return await handler(payload)

    async def _search(self, payload: dict) -> WorkerExecution:
        """Search the knowledge graph for context relevant to a query.

        Input payload:
          - query: str (required)
          - intent: str (optional, auto-classified if missing)
          - scope: str (optional)

        Output (matches SKILL.md contract):
          - snippets: list[str]
          - confidence: float
          - intent: str
          - refs: list[str]
        """
        query = payload.get("query", "")
        if not query:
            return WorkerExecution(
                ok=False,
                message="KG search requires a 'query' in payload",
            )

        if payload.get("demo_mode") or os.environ.get("PORTTHON_OFFLINE_MODE") == "1":
            return WorkerExecution(
                ok=True,
                message="KG demo context generated",
                data={
                    "snippets": [
                        "Public/private confidence delta is present.",
                        "Learning time currently outpaces conversion actions.",
                        "Financial stress is linked to execution drag.",
                        "ADHD-compatible chunking improves completion rate.",
                    ],
                    "confidence": 0.88,
                    "intent": payload.get("intent") or classify_intent(query),
                    "refs": ["c_0001", "t_0120", "ll_0142", "cal_0078"],
                },
            )

        # Classify intent
        intent = payload.get("intent") or classify_intent(query)
        mode = INTENT_TO_MODE.get(intent)

        logger.info(
            "KG search: query=%r intent=%s mode=%s",
            query[:80], intent, mode,
        )

        # Some intents skip KG entirely (emotional, casual)
        if mode is None:
            logger.info("KG search: intent '%s' — skipping retrieval", intent)
            return WorkerExecution(
                ok=True,
                message=f"Intent '{intent}' does not require KG context",
                data={
                    "snippets": [],
                    "confidence": 0.0,
                    "intent": intent,
                    "refs": [],
                },
            )

        # Query the KG
        rag = _create_rag_instance()
        if rag is None:
            logger.warning("KG search: RAG not available — returning empty context")
            return WorkerExecution(
                ok=True,
                message="KG not configured — returning empty context",
                data={
                    "snippets": [],
                    "confidence": 0.0,
                    "intent": intent,
                    "refs": [],
                },
            )

        try:
            from lightrag import QueryParam

            result = await rag.aquery(
                query,
                param=QueryParam(mode=mode, only_need_context=True),
            )

            if result is None:
                logger.info("KG search: no results for query=%r", query[:80])
                return WorkerExecution(
                    ok=True,
                    message="KG returned no results",
                    data={
                        "snippets": [],
                        "confidence": 0.0,
                        "intent": intent,
                        "refs": [],
                    },
                )

            context = result.content if hasattr(result, "content") else str(result)

            # Filter out empty or failed results
            if not context or context.strip() == "" or "fail" in context.lower()[:50]:
                logger.info("KG search: empty/failed result for query=%r", query[:80])
                return WorkerExecution(
                    ok=True,
                    message="KG returned empty or failed result",
                    data={
                        "snippets": [],
                        "confidence": 0.0,
                        "intent": intent,
                        "refs": [],
                    },
                )

            # Split context into snippets and compute confidence
            snippets = [s.strip() for s in context.split("\n\n") if s.strip()]
            confidence = min(1.0, len(snippets) * 0.2)

            logger.info(
                "KG search: found %d snippets, confidence=%.2f for query=%r",
                len(snippets), confidence, query[:80],
            )

            return WorkerExecution(
                ok=True,
                message=f"KG found {len(snippets)} relevant snippets",
                data={
                    "snippets": snippets,
                    "confidence": confidence,
                    "intent": intent,
                    "refs": [],  # TODO: extract entity refs from graph
                    "raw_context": context,  # full text for prompt injection
                },
            )

        except Exception as e:
            logger.error("KG search failed: %s", e, exc_info=True)
            return WorkerExecution(
                ok=False,
                message=f"KG search error: {e}",
                data={
                    "snippets": [],
                    "confidence": 0.0,
                    "intent": intent,
                    "refs": [],
                },
            )

    async def _classify(self, payload: dict) -> WorkerExecution:
        """Classify the intent of a query without searching.

        Useful for routing decisions in the master loop.
        """
        query = payload.get("query", "")
        intent = classify_intent(query)
        return WorkerExecution(
            ok=True,
            message=f"Intent classified as '{intent}'",
            data={"intent": intent, "query": query},
        )
