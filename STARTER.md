# Starter Guide — Hyperpersonalized Agent

## Prerequisites

- Python 3.10+
- Neo4j + Qdrant already populated (via previous LightRAG ingestion)
- Environment variables configured in `LightRAG/.env`

## Quick Start

```bash
# 1. Clone and switch to branch
git clone https://github.com/Tar-ive/porthon.git
cd porthon
git checkout vector_db

# 2. Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install -e LightRAG

# 3. Verify your .env is set up
# All config lives in LightRAG/.env — check these are set:
grep -E "^(NEO4J_URI|QDRANT_URL|LLM_MODEL|LLM_BINDING|EMBEDDING_MODEL)" LightRAG/.env

# You should see:
#   NEO4J_URI=neo4j+s://...
#   QDRANT_URL=https://...
#   LLM_MODEL=x-ai/grok-4.1-fast
#   LLM_BINDING=openai
#   EMBEDDING_MODEL=text-embedding-3-large

# 4. Start the agent server
cd agent
python server.py

# You should see:
#   Qdrant collection: lightrag_vdb_entities_text_embedding_3_large_3072d
#   [base] Connected to neo4j at neo4j+s://...
#   LightRAG initialized successfully
#   Uvicorn running on http://0.0.0.0:8888

# 5. Open the web UI
# Go to http://localhost:8888 in your browser
```

## What to Try

| Prompt | What happens |
|--------|-------------|
| "how much have I been spending on subscriptions?" | **Factual** — queries KG in `mix` mode (entities + chunks) |
| "do you notice any patterns in my behavior?" | **Pattern** — queries KG in `global` mode (relationships) |
| "should I take a client at $800 for a brand identity?" | **Advice** — queries KG in `hybrid` mode + profiler context |
| "I'm overwhelmed" | **Emotional** — no KG fetch, responds from SOUL.md personality |
| "hey what's up" | **Casual** — no KG fetch, just vibes |

## File Structure

```
porthon/
├── agent/
│   ├── server.py           # FastAPI + WebSocket server (main entry point)
│   ├── retriever.py         # LightRAG wrapper, intent → KG query routing
│   ├── prompt_builder.py    # Assembles SOUL + USER + KG context into prompt
│   ├── intent.py            # Intent classifier (keyword-based)
│   ├── SOUL.md              # Agent personality (archetype-driven)
│   └── USER.md              # User profile (KG-enriched)
├── web/
│   └── index.html           # Chat UI (single page, WebSocket)
├── data/                    # Raw JSONL data sources
├── profiler.py              # CrossPlatformProfiler
├── LightRAG/                # RAG framework (Neo4j + Qdrant backends)
│   └── .env                 # All database + API credentials
├── docs/
│   ├── AGENT_ARCHITECTURE.md
│   └── IMPLEMENTATION_PLAN.md
├── requirements.txt
└── STARTER.md               # This file
```

## Configuration

All config is read from `LightRAG/.env`. Key variables:

| Variable | Purpose |
|----------|---------|
| `NEO4J_URI` | Neo4j connection string |
| `NEO4J_USERNAME` / `NEO4J_PASSWORD` | Neo4j auth |
| `QDRANT_URL` / `QDRANT_API_KEY` | Qdrant connection |
| `LLM_BINDING_HOST` | LLM API base URL (OpenRouter) |
| `LLM_BINDING_API_KEY` | LLM API key |
| `LLM_MODEL` | Chat model (e.g. `x-ai/grok-4.1-fast`) |
| `EMBEDDING_BINDING_HOST` | Embedding API base URL |
| `EMBEDDING_BINDING_API_KEY` | Embedding API key |
| `EMBEDDING_MODEL` | Embedding model (e.g. `text-embedding-3-large`) |
| `EMBEDDING_DIM` | Embedding dimension (e.g. `3072`) |

The agent server port defaults to `8888`. Override with `AGENT_PORT` env var.

## Troubleshooting

**Server crashes on startup (OOM)**
- This machine has ~4GB RAM. Close other processes or add swap:
  ```bash
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  ```

**"Qdrant collection ... missing suffix" warning**
- Means `model_name` wasn't set on the embedding function. The current code sets it correctly.

**Empty KG results**
- Verify data exists: check Neo4j browser or run:
  ```bash
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

**First query is slow**
- Normal. LightRAG initializes LLM + embedding worker pools on first call. Subsequent queries are faster.
