# Porthon — Getting Started

## Prerequisites

- **Node.js** 18+ and **pnpm** (`npm install -g pnpm`)
- **Python 3.13+** and **uv** (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- An **OpenAI API key** (or a local Ollama instance)

## Quick Start

```bash
git clone https://github.com/Tar-ive/porthon.git
cd porthon
git checkout milestone1_kusum

# Configure environment
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY

# Install dependencies & start
make install
make dev
```

Open **http://localhost:8000** in your browser.

## Optional: Knowledge Graph (LightRAG + Neo4j + Qdrant)

The agent intelligence layer (intent classification, personality system, KG-augmented responses) activates automatically when you provide the optional environment variables.

Without them, chat works normally using just the OpenAI/Ollama backend.

### Setup

1. **Neo4j** — [Neo4j Aura](https://neo4j.com/cloud/aura/) (free tier) or local Docker:
   ```bash
   docker run -d --name neo4j -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5
   ```

2. **Qdrant** — [Qdrant Cloud](https://cloud.qdrant.io/) (free tier) or local Docker:
   ```bash
   docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
   ```

3. Add to your `.env`:
   ```
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=password
   QDRANT_URL=http://localhost:6333

   # LLM for LightRAG graph construction
   LLM_BINDING_API_KEY=your-openrouter-key
   LLM_BINDING_HOST=https://openrouter.ai/api/v1
   LLM_MODEL=x-ai/grok-4.1-fast

   # Embeddings
   EMBEDDING_BINDING_API_KEY=your-openai-key
   EMBEDDING_BINDING_HOST=https://api.openai.com/v1
   EMBEDDING_MODEL=text-embedding-3-large
   EMBEDDING_DIM=3072
   ```

4. Restart: `make dev`

The chat will now classify intents (factual, pattern, advice, reflection, emotional) and retrieve relevant context from the knowledge graph. Intent badges appear on messages in the UI.
