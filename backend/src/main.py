"""
main.py — FastAPI server for the Vectorless System Design Assistant.

Endpoints:
  POST /query — Query the knowledge base
  POST /query/debug — Query with debug information
  GET /health — Health check
  GET /stats — Cache & KB stats
  POST /cache/clear — Clear query cache (requires X-Admin-Key if ADMIN_API_KEY is set)
"""

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import backend modules
import sys
sys.path.insert(0, os.path.dirname(__file__))

from llm import call_llm_async
from logging_config import configure_logging
from middleware import register_tracing
from query_analyzer import analyze_query
from navigator import navigate_tree, compute_confidence
from answer_generator import generate_answer, extract_excerpt
from secrets_manager import get_secret

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_KB_PATH = "data/kb/knowledge_base.json"
KB_PATH = os.getenv("KB_PATH", DEFAULT_KB_PATH)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
MAX_QUERY_LENGTH = 500


# ============================================================================
# BOUNDED CACHE
# ============================================================================

class QueryCache:
    """Simple bounded cache with TTL-based expiration."""

    def __init__(self, maxsize: int = 500, ttl_seconds: int = 3600):
        self._store: dict = {}
        self._maxsize = maxsize
        self._ttl = ttl_seconds

    def get(self, key: str):
        entry = self._store.get(key)
        if entry is None:
            return None
        value, ts = entry
        if time.time() - ts > self._ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value):
        if len(self._store) >= self._maxsize and key not in self._store:
            # Evict oldest entry
            oldest_key = min(self._store, key=lambda k: self._store[k][1])
            del self._store[oldest_key]
        self._store[key] = (value, time.time())

    def clear(self):
        self._store.clear()

    def __len__(self):
        return len(self._store)

    def keys(self):
        return list(self._store.keys())


# ============================================================================
# STATE
# ============================================================================

KB = {}
KB_LOADED = False
query_cache = QueryCache(maxsize=500, ttl_seconds=3600)


# ============================================================================
# MODELS
# ============================================================================

class QueryRequest(BaseModel):
    query: str = Field(..., max_length=MAX_QUERY_LENGTH)
    provider: Optional[str] = LLM_PROVIDER
    use_debug: Optional[bool] = False
    deterministic: Optional[bool] = False


class QueryResponse(BaseModel):
    query: str
    answer: str
    best_node: str
    path: list
    confidence: float
    score: float
    cached: bool
    debug: Optional[dict] = None


# ============================================================================
# LIFESPAN (replaces deprecated @app.on_event)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load knowledge base on startup, cleanup on shutdown."""
    global KB, KB_LOADED

    if not os.path.exists(KB_PATH):
        logger.error("KB not found at %s", KB_PATH)
        KB_LOADED = False
    else:
        try:
            with open(KB_PATH, "r") as f:
                KB = json.load(f)
            KB_LOADED = True
            first_key = next(iter(KB)) if KB else None
            logger.info("KB loaded: %s (root: %s)", KB_PATH, first_key)
        except Exception as e:
            logger.error("Failed to load KB: %s", e)
            KB_LOADED = False

    # If configured provider is Groq but no API key is present, fall back to Ollama
    global LLM_PROVIDER
    if LLM_PROVIDER == "groq":
        try:
            groq_key = get_secret("GROQ_API_KEY", required=False)
        except Exception:
            groq_key = None
        if not groq_key:
            logger.warning(
                "GROQ_API_KEY not found; falling back to 'ollama' provider. "
                "Set GROQ_API_KEY in backend/config/.env or environment to use Groq."
            )
            LLM_PROVIDER = "ollama"

    yield

    # Shutdown cleanup
    query_cache.clear()
    logger.info("Shutdown complete")


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Vectorless System Design Assistant",
    description="Tree-based knowledge base navigation with LLM guidance",
    version="1.0.0",
    lifespan=lifespan,
)

# Initialize structured logging
configure_logging()

# Register tracing middleware (adds X-Request-ID and request logs)
register_tracing(app)

# Enable CORS (allow_credentials=False since origins is wildcard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "kb_loaded": KB_LOADED,
        "kb_path": KB_PATH,
    }


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest):
    """Main query endpoint."""
    if not KB_LOADED or not KB:
        raise HTTPException(status_code=503, detail="Knowledge base not loaded")

    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # Check cache
    cached_result = query_cache.get(query)
    if cached_result is not None:
        cached_result["cached"] = True
        return cached_result

    # Analyze query
    try:
        analysis = await analyze_query(query, provider=req.provider)
        keywords = analysis.get("keywords", [])
    except Exception as e:
        logger.warning("Query analysis error: %s", e)
        keywords = []

    # Navigate tree
    root = KB.get("System Design", {})
    if not root:
        raise HTTPException(status_code=500, detail="KB root node not found")

    try:
        nav_result = await navigate_tree(
            query,
            keywords,
            root,
            max_depth=5,
            provider=req.provider,
            debug=req.use_debug,
            deterministic=bool(req.deterministic),
        )
    except Exception as e:
        logger.error("Navigation error: %s", e)
        raise HTTPException(status_code=500, detail="Navigation failed")

    # Generate answer
    best_node = nav_result["best_node"]
    best_node_name = nav_result["best_node_name"]
    path = nav_result["path"]
    score = nav_result["score"]
    depth = nav_result["depth"]

    node_content = best_node.get("content", "")

    try:
        answer = await generate_answer(
            query,
            node_content,
            path,
            provider=req.provider,
        )
    except Exception as e:
        logger.warning("Answer generation error: %s", e)
        # Fallback: provide excerpt
        answer = f"From {best_node_name}:\n\n{extract_excerpt(node_content, 300)}"

    confidence = compute_confidence(score, depth)

    # Build response
    response = QueryResponse(
        query=query,
        answer=answer,
        best_node=best_node_name,
        path=path,
        confidence=confidence,
        score=score,
        cached=False,
        debug=None,
    )

    if req.use_debug:
        response.debug = {
            "keywords": keywords,
            "intent": analysis.get("intent", "unknown"),
            "depth": depth,
            "node_content_length": len(node_content),
            "deterministic": bool(req.deterministic),
        }

    # Cache result
    response_dict = response.dict()
    query_cache.set(query, response_dict)

    return response


@app.post("/query/debug", response_model=QueryResponse)
async def query_debug_endpoint(req: QueryRequest):
    """Query endpoint with debug information."""
    req.use_debug = True
    return await query_endpoint(req)


@app.get("/stats")
async def stats():
    """Get cache and KB statistics."""
    if not KB_LOADED:
        return {"status": "KB not loaded"}

    def count_nodes(node):
        """Count total nodes in KB tree."""
        count = 1
        children = node.get("children", {}) or node.get("subtopics", {})
        for child in children.values():
            count += count_nodes(child)
        return count

    root = KB.get("System Design", {})
    total_nodes = count_nodes(root) if root else 0

    return {
        "kb_loaded": KB_LOADED,
        "kb_path": KB_PATH,
        "total_nodes": total_nodes,
        "cached_queries": len(query_cache),
        "cache_keys": query_cache.keys(),
    }


@app.post("/cache/clear")
async def clear_cache(request: Request):
    """Clear the query cache. Requires X-Admin-Key header if ADMIN_API_KEY is set."""
    if ADMIN_API_KEY:
        auth_header = request.headers.get("X-Admin-Key", "")
        if auth_header != ADMIN_API_KEY:
            raise HTTPException(status_code=403, detail="Invalid admin key")

    count = len(query_cache)
    query_cache.clear()
    return {"status": "cleared", "cleared_count": count}


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting server...")
    logger.info("  KB Path: %s", KB_PATH)
    logger.info("  LLM Provider: %s", LLM_PROVIDER)
    logger.info("  Debug: %s", DEBUG)
    logger.info("  Host: %s, Port: %d", HOST, PORT)

    uvicorn.run(app, host=HOST, port=PORT)