"""
main.py — FastAPI server for the Vectorless System Design Assistant.

Endpoints:
  POST /query — Query the knowledge base
  POST /query/debug — Query with debug information
  GET /health — Health check
  GET /stats — Cache & KB stats
  POST /cache/clear — Clear query cache
"""

import json
import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import backend modules
import sys
sys.path.insert(0, os.path.dirname(__file__))

from llm import call_llm_async
from logging_config import configure_logging
from middleware import register_tracing
from query_analyzer import analyze_query
from navigator import navigate_tree, compute_confidence
from answer_generator import generate_answer, extract_excerpt


# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_KB_PATH = "shared/data/kb/knowledge_base.json"
LEGACY_KB_PATH = "data/kb/knowledge_base.json"
KB_PATH = os.getenv("KB_PATH", DEFAULT_KB_PATH)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 8000))


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Vectorless System Design Assistant",
    description="Tree-based knowledge base navigation with LLM guidance",
    version="1.0.0",
)

# Initialize structured logging
configure_logging()

# Register tracing middleware (adds X-Request-ID and request logs)
register_tracing(app)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# STATE
# ============================================================================

# Knowledge base (loaded at startup)
KB = {}
KB_LOADED = False

# Query cache
query_cache = {}


# ============================================================================
# MODELS
# ============================================================================

class QueryRequest(BaseModel):
    query: str
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
# STARTUP / SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Load knowledge base on startup."""
    global KB, KB_LOADED, KB_PATH

    if not os.path.exists(KB_PATH) and KB_PATH == DEFAULT_KB_PATH and os.path.exists(LEGACY_KB_PATH):
        print(f"ℹ Using legacy KB path: {LEGACY_KB_PATH}")
        KB_PATH = LEGACY_KB_PATH

    if not os.path.exists(KB_PATH):
        print(f"⚠️  KB not found at {KB_PATH}")
        KB_LOADED = False
        return
    
    try:
        with open(KB_PATH, "r") as f:
            KB = json.load(f)
        KB_LOADED = True
        print(f"✓ KB loaded: {KB_PATH}")
        print(f"  Root: {first_key(KB)}")
    except Exception as e:
        print(f"✗ Failed to load KB: {e}")
        KB_LOADED = False


def first_key(d: dict):
    """Get first key from dict."""
    return next(iter(d)) if d else None


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
    """
    Main query endpoint.
    
    POST /query
    {
      "query": "How does consistent hashing work?",
      "provider": "ollama",
            "use_debug": false,
            "deterministic": false
    }
    """
    if not KB_LOADED or not KB:
        raise HTTPException(status_code=503, detail="Knowledge base not loaded")
    
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Check cache
    cached = query in query_cache
    if cached:
        cached_result = query_cache[query]
        cached_result["cached"] = True
        return cached_result
    
    # Analyze query
    try:
        analysis = await analyze_query(query, provider=req.provider)
        keywords = analysis.get("keywords", [])
    except Exception as e:
        if DEBUG:
            print(f"Query analysis error: {e}")
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
        if DEBUG:
            print(f"Navigation error: {e}")
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
        if DEBUG:
            print(f"Answer generation error: {e}")
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
    query_cache[query] = response_dict
    
    return response


@app.post("/query/debug", response_model=QueryResponse)
async def query_debug_endpoint(req: QueryRequest):
    """
    Query endpoint with debug information.
    
    POST /query/debug
    {
      "query": "What is a load balancer?",
      "provider": "ollama"
    }
    """
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
        "cache_keys": list(query_cache.keys()),
    }


@app.post("/cache/clear")
async def clear_cache():
    """Clear the query cache."""
    global query_cache
    count = len(query_cache)
    query_cache = {}
    return {"status": "cleared", "cleared_count": count}


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print(f"Starting server...")
    print(f"  KB Path: {KB_PATH}")
    print(f"  LLM Provider: {LLM_PROVIDER}")
    print(f"  Debug: {DEBUG}")
    print(f"  Host: {HOST}, Port: {PORT}")
    print()
    
    uvicorn.run(app, host=HOST, port=PORT)
