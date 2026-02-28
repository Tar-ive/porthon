# Starter Guide — Hyperpersonalized Agent

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- Neo4j + Qdrant already populated (via previous LightRAG ingestion)
- Environment variables configured in `LightRAG/.env`

---

## Build, Setup, and Run Commands

### 1. Clone and checkout

```bash
git clone https://github.com/Tar-ive/porthon.git
cd porthon
git checkout vector_db
```

### 2. Python environment

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e "LightRAG[api]"
```

### 3. Web dependencies

```bash
cd web
npm install
npm install @vitejs/plugin-react react react-dom
```

### 4. Verify environment

```bash
grep -E "^(NEO4J_URI|QDRANT_URL|LLM_MODEL|LLM_BINDING|EMBEDDING_MODEL)" LightRAG/.env
```

Expected output:
```
NEO4J_URI=neo4j+s://...
QDRANT_URL=https://...
LLM_MODEL=x-ai/grok-4.1-fast
LLM_BINDING=openai
EMBEDDING_MODEL=text-embedding-3-large
```

### 4. Start the backend (Terminal 1)

```bash
source .venv/bin/activate
cd LightRAG
python -m lightrag.api.lightrag_server
```

Expected startup log:
```
Qdrant collection: lightrag_vdb_entities_text_embedding_3_large_3072d
[base] Connected to neo4j at neo4j+s://...
LightRAG initialized successfully
Uvicorn running on http://0.0.0.0:9621
```

### 5. Start the frontend (Terminal 2)

```bash
cd web
npm install
npm run dev
```

Expected output:
```
VITE v7.x.x  ready in XXXms
➜  Local:   http://localhost:8888/
```

### 6. Open the app

Go to **http://localhost:8888** in your browser.

---

## How It Works

### LLM Configuration

The agent uses the **same OpenRouter config** from `LightRAG/.env`:
- `LLM_BINDING_HOST=https://openrouter.ai/api/v1` — OpenRouter API
- `LLM_BINDING_API_KEY` — your OpenRouter key
- `LLM_MODEL=x-ai/grok-4.1-fast` — the chat model

No separate API keys needed. Everything comes from `LightRAG/.env`.

### Intent-Based KG Retrieval

Not every message queries the knowledge graph. The agent classifies intent first:

| Your Message | Intent | What Happens |
|-------------|--------|-------------|
| "how much did I spend on subscriptions?" | `factual` | KG query: `mix` mode (entities + relationships + chunks) |
| "do you notice any patterns?" | `pattern` | KG query: `global` mode (relationship-centric) |
| "should I take this client at $800?" | `advice` | KG query: `hybrid` mode + profiler context |
| "I'm overwhelmed" | `emotional` | No KG. Responds from SOUL.md personality only |
| "hey what's up" | `casual` | No KG. Just vibes |

### Agent Personality

Defined in `agent/SOUL.md`:
- Mirrors your vocabulary (if you say "freaking out", so does it)
- Matches message length to yours
- Names patterns once, doesn't lecture
- Never says "the data shows" — just knows things
- ADHD-aware: short, chunked, bold the one action
- Financial-aware: concrete tools, not motivational platitudes

---

## Project Structure

```
porthon/
├── web/                      # Frontend (React + Vite)
│   ├── src/App.jsx           # Chat component
│   ├── src/App.css           # Styles
│   ├── vite.config.js        # Dev proxy → backend:9621
│   └── package.json
├── LightRAG/                 # RAG framework + Backend API
│   ├── lightrag/api/         # FastAPI server (port 9621)
│   │   └── lightrag_server.py
│   └── .env                  # All credentials (Neo4j, Qdrant, OpenRouter, OpenAI)
├── docs/
│   ├── AGENT_ARCHITECTURE.md # Deep research doc
│   └── IMPLEMENTATION_PLAN.md
├── requirements.txt          # Python deps
└── STARTER.md                # This file
```

## Configuration Reference

All config lives in `LightRAG/.env`:

| Variable | Purpose |
|----------|---------|
| `NEO4J_URI` | Neo4j connection (cloud) |
| `NEO4J_USERNAME` / `NEO4J_PASSWORD` | Neo4j auth |
| `QDRANT_URL` / `QDRANT_API_KEY` | Qdrant connection (cloud) |
| `LLM_BINDING_HOST` | OpenRouter API base URL |
| `LLM_BINDING_API_KEY` | OpenRouter API key |
| `LLM_MODEL` | Chat model (`x-ai/grok-4.1-fast`) |
| `EMBEDDING_BINDING_HOST` | OpenAI embeddings base URL |
| `EMBEDDING_BINDING_API_KEY` | OpenAI API key (for embeddings only) |
| `EMBEDDING_MODEL` | `text-embedding-3-large` |
| `EMBEDDING_DIM` | `3072` |
| `WHITELIST_PATHS` | `/health,/api/*,/query` (required for frontend) |

Agent port: `9621` (LightRAG server, override with `LIGHTRAG_PORT` env var).
Frontend dev port: `8888` (Vite proxies `/query` and `/chat` to backend).

---

## Troubleshooting

**Server killed / OOM:**
This machine has ~4GB RAM. Add swap if needed:
```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
```

**First query is slow:**
Normal. LightRAG initializes LLM + embedding worker pools on first call.

**Empty KG results:**
```bash
source .venv/bin/activate
python -c "
from dotenv import load_dotenv; load_dotenv('LightRAG/.env')
import asyncio, os
from neo4j import AsyncGraphDatabase
async def check():
    d = AsyncGraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USERNAME'), os.getenv('NEO4J_PASSWORD')))
    async with d.session(database='neo4j') as s:
        r = await s.run('MATCH (n:base) RETURN count(n) as c')
        print('Nodes:', (await r.single())['c'])
    await d.close()
asyncio.run(check())
"
```
