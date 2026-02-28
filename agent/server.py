"""
Hyperpersonalized Agent — FastAPI server with WebSocket chat.
Connects to Neo4j + Qdrant via LightRAG for KG-aware retrieval.
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager

# Load .env from LightRAG directory (where all the DB credentials live)
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / "LightRAG" / ".env"
load_dotenv(dotenv_path=str(env_path), override=False)

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "LightRAG"))
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from retriever import create_rag_instance, retrieve_context
from prompt_builder import build_system_prompt
from intent import classify_intent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Global state ────────────────────────────────────────────────

rag_instance = None
conversation_histories: dict[str, list] = {}  # session_id -> messages


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize LightRAG on startup, cleanup on shutdown."""
    global rag_instance
    logger.info("Initializing LightRAG (Neo4j + Qdrant)...")
    rag_instance = create_rag_instance()
    await rag_instance.initialize_storages()
    logger.info("LightRAG initialized successfully")
    yield
    # Cleanup
    if rag_instance:
        await rag_instance.finalize_storages()
    logger.info("Shutdown complete")


app = FastAPI(title="Hyperpersonalized Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── LLM call ────────────────────────────────────────────────────

async def call_llm(system_prompt: str, messages: list[dict]) -> str:
    """Call the LLM with system prompt and conversation history."""
    from openai import AsyncOpenAI
    
    client = AsyncOpenAI(
        api_key=os.getenv("LLM_BINDING_API_KEY"),
        base_url=os.getenv("LLM_BINDING_HOST", "https://openrouter.ai/api/v1"),
    )
    
    llm_messages = [{"role": "system", "content": system_prompt}]
    llm_messages.extend(messages)
    
    response = await client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "x-ai/grok-4.1-fast"),
        messages=llm_messages,
        temperature=0.7,
        max_tokens=1024,
    )
    
    return response.choices[0].message.content


async def call_llm_stream(system_prompt: str, messages: list[dict]):
    """Stream LLM response token by token."""
    from openai import AsyncOpenAI
    
    client = AsyncOpenAI(
        api_key=os.getenv("LLM_BINDING_API_KEY"),
        base_url=os.getenv("LLM_BINDING_HOST", "https://openrouter.ai/api/v1"),
    )
    
    llm_messages = [{"role": "system", "content": system_prompt}]
    llm_messages.extend(messages)
    
    stream = await client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "x-ai/grok-4.1-fast"),
        messages=llm_messages,
        temperature=0.7,
        max_tokens=1024,
        stream=True,
    )
    
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


# ── Chat handler ────────────────────────────────────────────────

async def handle_chat(query: str, session_id: str = "default") -> str:
    """Main chat handler: intent → retrieve → prompt → respond."""
    
    # Get or create conversation history
    if session_id not in conversation_histories:
        conversation_histories[session_id] = []
    
    history = conversation_histories[session_id]
    
    # Add user message to history
    history.append({"role": "user", "content": query})
    
    # Keep only last 20 messages for context window management
    if len(history) > 20:
        history = history[-20:]
        conversation_histories[session_id] = history
    
    # Retrieve KG context based on intent
    context, intent = await retrieve_context(query, rag_instance)
    
    logger.info(f"[{session_id}] Intent: {intent} | Context: {'yes' if context else 'no'} ({len(context) if context else 0} chars)")
    
    # Build system prompt
    system_prompt = build_system_prompt(context=context, intent=intent)
    
    # Call LLM
    response = await call_llm(system_prompt, history)
    
    # Add assistant response to history
    history.append({"role": "assistant", "content": response})
    
    return response


# ── API routes ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    intent: str


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """HTTP chat endpoint."""
    intent = classify_intent(req.message)
    response = await handle_chat(req.message, req.session_id)
    return ChatResponse(response=response, intent=intent)


@app.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket chat endpoint with streaming."""
    await websocket.accept()
    logger.info(f"WebSocket connected: {session_id}")
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            query = msg.get("message", "")
            
            if not query.strip():
                continue
            
            # Get or create conversation history
            if session_id not in conversation_histories:
                conversation_histories[session_id] = []
            history = conversation_histories[session_id]
            history.append({"role": "user", "content": query})
            
            if len(history) > 20:
                history = history[-20:]
                conversation_histories[session_id] = history
            
            # Retrieve context
            context, intent = await retrieve_context(query, rag_instance)
            system_prompt = build_system_prompt(context=context, intent=intent)
            
            # Send intent info
            await websocket.send_text(json.dumps({
                "type": "meta",
                "intent": intent,
                "has_context": context is not None,
            }))
            
            # Stream response
            full_response = ""
            async for token in call_llm_stream(system_prompt, history):
                full_response += token
                await websocket.send_text(json.dumps({
                    "type": "token",
                    "content": token,
                }))
            
            # Send completion signal
            await websocket.send_text(json.dumps({
                "type": "done",
                "content": full_response,
            }))
            
            # Save to history
            history.append({"role": "assistant", "content": full_response})
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass


@app.get("/health")
async def health():
    return {"status": "ok", "rag_initialized": rag_instance is not None}


# ── Entry point ─────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("AGENT_PORT", "8888"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
