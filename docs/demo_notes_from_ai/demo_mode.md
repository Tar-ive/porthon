# Demo Mode with Local KG Data

## Overview

Demo mode uses local rag_storage data to provide fast, self-contained KG queries without requiring Neo4j/Qdrant connections.

## Constraints

- **Only supports Theo (p05)** - no other personas
- **No external API calls** - uses pre-indexed local data

## Data Sources

| Source | Location | Size | Use |
|--------|----------|------|-----|
| Entities | `rag_storage/kv_store_full_entities.json` | 9 items | Entity search, context |
| Relations | `rag_storage/kv_store_full_relations.json` | 9 items | Relationship context |
| Text Chunks | `rag_storage/kv_store_text_chunks.json` | 44 items | RAG content |
| Doc Status | `rag_storage/kv_store_doc_status.json` | 9 items | Document metadata |
| LLM Cache | `rag_storage/kv_store_llm_response_cache.json` | 133 items | Cached responses |

**Total: ~2.8 MB of pre-indexed data**

## Entity Examples (Theo Nakamura)

```
Theo Nakamura
├── Tools: ChatGPT, Midjourney, Figma, Notion, Instagram, Discord, Adobe Firefly
├── Locations: Austin, TX, East Austin, Local Coffee Shop
├── Work: Self-Employed
├── Social: Twitter/X, TikTok, Instagram
├── Projects: Data Portability Hackathon 2026
```

## Implementation Plan

### 1. Create Demo KG Loader (`app/kg_demo.py`)

```python
class DemoKG:
    """Lightweight KG that reads from rag_storage JSON files."""
    
    def __init__(self, storage_dir: str = "rag_storage"):
        self.entities = json.load(open(f"{storage_dir}/kv_store_full_entities.json"))
        self.relations = json.load(open(f"{storage_dir}/kv_store_full_relations.json"))
        self.chunks = json.load(open(f"{storage_dir}/kv_store_text_chunks.json"))
    
    def search(self, query: str) -> list[str]:
        # Simple keyword match on entity names
        results = []
        for doc_id, entity_data in self.entities.items():
            for name in entity_data.get("entity_names", []):
                if query.lower() in name.lower():
                    results.append(name)
        return results[:5]
    
    def get_related(self, entity: str) -> list[str]:
        # Find relations for entity
        ...
```

### 2. Update Demo Mode Flow

When `Authorization: Bearer sk_demo_p5` is used:
- Skip LLM calls for scenario generation (use pre-cached or fallback)
- Use `DemoKG` for context retrieval instead of real Neo4j/Qdrant
- Return mock Composio responses (already implemented)

### 3. File Changes

| File | Change |
|------|--------|
| `app/kg_demo.py` | NEW - Demo KG loader |
| `app/auth.py` | Update to enable demo KG when in demo mode |
| `main.py` | Remove KG init from startup, lazy load |

## Performance

| Mode | Startup Time | KG Query |
|------|-------------|----------|
| Live (Neo4j+Qdrant) | ~30s | ~100ms |
| Demo (local JSON) | ~0.5s | ~10ms |

## Auth Keys

| Key | Mode | Persona | Temperature |
|-----|------|---------|-------------|
| `sk_live_*` | live | p05 | 0.7 |
| `sk_demo_*` | test | p05 | 0.0 |
| `sk_demo_p5` | demo | p05 | 0.0 |

## Files Affected

```
src/backend/
├── app/
│   ├── kg_demo.py          # NEW - Demo KG loader
│   ├── auth.py             # MODIFY - Enable demo KG in demo mode
│   └── api/v1/
│       └── scenarios.py     # MODIFY - Use demo KG for context
├── main.py                 # MODIFY - Lazy KG load
└── rag_storage/            # EXISTING - Pre-indexed KG data

docs/demo_notes_from_ai/
└── demo_mode.md           # NEW - This document
```
