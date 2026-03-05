"""V1 Knowledge Graph endpoint — serves entities and relations from rag_storage."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

RAG_DIR = Path(__file__).resolve().parents[3] / "rag_storage"

# Heuristic category assignment for KG nodes
_TOOL_KEYWORDS = {
    "figma", "blender", "notion", "instagram", "tiktok", "twitter", "discord",
    "chatgpt", "midjourney", "runway ml", "adobe", "trello", "google sheets",
    "after effects", "rive", "canopy", "zoom", "zelle", "chase", "uber",
    "linkedin", "school of motion", "motion design school",
}
_PLACE_KEYWORDS = {
    "austin", "east austin", "downtown", "café", "cafe", "coffee shop",
    "ut library", "barton springs", "6th street", "home", "home studio",
}
_FINANCIAL_KEYWORDS = {
    "credit card", "debt", "rent", "invoice", "payment", "expenses",
    "revenue", "taxes", "freelance income", "cost of living", "401k",
    "bank", "subscriptions", "groceries", "budget", "balance",
}
_PERSON_KEYWORDS = {"theo nakamura", "theo", "jake", "roommate", "roommates", "client"}


def _categorize(label: str) -> str:
    low = label.lower().strip()
    if any(k in low for k in _PERSON_KEYWORDS):
        return "person"
    if any(k == low or low.startswith(k) for k in _TOOL_KEYWORDS):
        return "tool"
    if any(k in low for k in _PLACE_KEYWORDS):
        return "place"
    if any(k in low for k in _FINANCIAL_KEYWORDS):
        return "financial"
    return "concept"


def _node_id(label: str) -> str:
    """Stable slug from label."""
    return re.sub(r"[^a-z0-9]+", "-", label.lower().strip()).strip("-")


def _load_graph():
    entities_path = RAG_DIR / "kv_store_full_entities.json"
    relations_path = RAG_DIR / "kv_store_full_relations.json"

    if not entities_path.exists() or not relations_path.exists():
        return {"nodes": [], "edges": [], "meta": {"total_nodes": 0, "total_edges": 0}}

    with open(entities_path) as f:
        entities_data = json.load(f)
    with open(relations_path) as f:
        relations_data = json.load(f)

    # Deduplicate entity names across all docs and count connections
    connection_count: dict[str, int] = defaultdict(int)
    all_entity_names: set[str] = set()

    for doc in entities_data.values():
        for name in doc.get("entity_names", []):
            all_entity_names.add(name)

    # Collect unique edges
    edge_set: set[tuple[str, str]] = set()
    for doc in relations_data.values():
        for pair in doc.get("relation_pairs", []):
            if len(pair) == 2:
                src, tgt = pair[0], pair[1]
                key = (min(src, tgt), max(src, tgt))  # normalize direction
                edge_set.add(key)
                connection_count[src] += 1
                connection_count[tgt] += 1

    # Build nodes
    nodes = []
    node_ids_seen: set[str] = set()
    for name in sorted(all_entity_names):
        nid = _node_id(name)
        if not nid or nid in node_ids_seen:
            continue
        node_ids_seen.add(nid)
        nodes.append({
            "id": nid,
            "label": name,
            "category": _categorize(name),
            "size": connection_count.get(name, 1),
        })

    # Build edges
    edges = []
    for idx, (src, tgt) in enumerate(sorted(edge_set)):
        src_id = _node_id(src)
        tgt_id = _node_id(tgt)
        if src_id in node_ids_seen and tgt_id in node_ids_seen:
            edges.append({"id": f"e_{idx}", "source": src_id, "target": tgt_id})

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {"total_nodes": len(nodes), "total_edges": len(edges)},
    }


@router.get("/knowledge-graph")
async def get_knowledge_graph():
    """Return the full knowledge graph (entities + relations) from rag_storage."""
    data = _load_graph()
    return {"object": "knowledge_graph", **data}


# ── Source type mapping from file names ─────────────────────────────
_SOURCE_TYPE_MAP = {
    "consent.json": "consent",
    "persona_profile.json": "profile",
    "calendar.json": "calendar",
    "conversations.json": "conversations",
    "emails.json": "email",
    "files_index.json": "files",
    "lifelog (1).json": "lifelog",
    "lifelog.json": "lifelog",
    "social_posts.json": "social",
    "transactions.json": "bank",
}

_SOURCE_ICONS = {
    "email": "📧",
    "calendar": "📅",
    "bank": "💳",
    "social": "📝",
    "lifelog": "📓",
    "files": "📁",
    "conversations": "💬",
    "profile": "👤",
    "consent": "🔒",
}


@router.get("/knowledge-graph/summary")
async def get_kg_summary():
    """Return processed data summary from rag_storage doc status."""
    doc_status_path = RAG_DIR / "kv_store_doc_status.json"
    if not doc_status_path.exists():
        return {"object": "kg_summary", "sources": [], "totals": {}}

    with open(doc_status_path) as f:
        doc_status = json.load(f)

    sources = []
    total_chunks = 0
    for doc in doc_status.values():
        file_name = doc.get("file_path", "unknown")
        source_type = _SOURCE_TYPE_MAP.get(file_name, "other")
        chunks = doc.get("chunks_count", 0)
        total_chunks += chunks
        sources.append({
            "type": source_type,
            "icon": _SOURCE_ICONS.get(source_type, "📄"),
            "file": file_name,
            "chunks": chunks,
            "content_length": doc.get("content_length", 0),
            "status": doc.get("status", "unknown"),
        })

    # Sort by content_length descending
    sources.sort(key=lambda s: s["content_length"], reverse=True)

    # Get entity/relation counts from graph
    graph_data = _load_graph()

    return {
        "object": "kg_summary",
        "sources": sources,
        "totals": {
            "docs": len(sources),
            "chunks": total_chunks,
            "entities": graph_data["meta"]["total_nodes"],
            "relations": graph_data["meta"]["total_edges"],
        },
    }


@router.get("/knowledge-graph/activity")
async def get_kg_activity():
    """Return recent processed documents from rag_storage."""
    doc_status_path = RAG_DIR / "kv_store_doc_status.json"
    if not doc_status_path.exists():
        return {"object": "list", "data": []}

    with open(doc_status_path) as f:
        doc_status = json.load(f)

    items = []
    for doc_id, doc in doc_status.items():
        file_name = doc.get("file_path", "unknown")
        source_type = _SOURCE_TYPE_MAP.get(file_name, "other")
        items.append({
            "id": doc_id,
            "file": file_name,
            "type": source_type,
            "icon": _SOURCE_ICONS.get(source_type, "📄"),
            "status": doc.get("status", "unknown"),
            "chunks": doc.get("chunks_count", 0),
            "content_length": doc.get("content_length", 0),
            "processed_at": doc.get("updated_at"),
            "created_at": doc.get("created_at"),
        })

    # Sort by processed_at descending
    items.sort(key=lambda x: x.get("processed_at") or "", reverse=True)

    return {"object": "list", "data": items}
