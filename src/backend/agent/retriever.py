"""
Retrieval orchestrator — decides when and how to query the KG.
Wraps LightRAG's query engine with intent-based routing.
"""

import logging
import os

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

from .intent import INTENT_TO_MODE, classify_intent

logger = logging.getLogger(__name__)


def create_rag_instance(working_dir: str | None = None) -> LightRAG:
    """
    Create a LightRAG instance configured for Neo4j + Qdrant.
    Reads all config from environment variables.
    """
    if working_dir is None:
        working_dir = os.path.join(os.path.dirname(__file__), "rag_storage")

    os.makedirs(working_dir, exist_ok=True)

    embedding_dim = int(os.getenv("EMBEDDING_DIM", "3072"))
    embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    llm_model = os.getenv("LLM_MODEL", "x-ai/grok-4.1-fast")
    llm_host = os.getenv("LLM_BINDING_HOST", "https://openrouter.ai/api/v1")
    llm_api_key = os.getenv("LLM_BINDING_API_KEY", "")
    embedding_host = os.getenv("EMBEDDING_BINDING_HOST", "https://api.openai.com/v1")
    embedding_api_key = os.getenv("EMBEDDING_BINDING_API_KEY", "")
    cosine_threshold = float(os.getenv("COSINE_THRESHOLD", "0.2"))

    async def llm_func(prompt, system_prompt=None, history_messages=[], **kwargs):
        return await openai_complete_if_cache(
            llm_model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=llm_api_key,
            base_url=llm_host,
            **kwargs,
        )

    async def embed_func(texts: list[str]) -> list[list[float]]:
        return await openai_embed(
            texts,
            model=embedding_model,
            api_key=embedding_api_key,
            base_url=embedding_host,
        )

    embedding = EmbeddingFunc(
        embedding_dim=embedding_dim,
        max_token_size=8192,
        func=embed_func,
        model_name=embedding_model,
    )

    rag = LightRAG(
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

    return rag


async def retrieve_context(query: str, rag: LightRAG) -> tuple[str | None, str]:
    """
    Decide if/how to query the KG based on intent, return (context, intent).
    """
    intent = classify_intent(query)
    mode = INTENT_TO_MODE.get(intent)

    if mode is None:
        logger.info(f"Intent '{intent}' — skipping KG retrieval")
        return None, intent

    logger.info(f"Intent '{intent}' — querying KG in '{mode}' mode")

    try:
        result = await rag.aquery(
            query,
            param=QueryParam(mode=mode, only_need_context=True),
        )

        if result is None:
            return None, intent

        context = result.content if hasattr(result, "content") else str(result)

        if not context or context.strip() == "" or "fail" in context.lower()[:50]:
            return None, intent

        return context, intent

    except Exception as e:
        logger.error(f"KG retrieval failed: {e}")
        return None, intent
