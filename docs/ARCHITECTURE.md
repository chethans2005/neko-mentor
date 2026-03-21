# Vectorless System Design Assistant - Architecture & Implementation Guide

This document provides a comprehensive overview of the backend implementation.

## System Overview

The **Vectorless System Design Assistant** is a tree-based LLM-guided navigation system that answers system design questions without using vector embeddings or semantic search.

### Key Principles

1. **No Vector DBs** — Uses hierarchical tree traversal instead
2. **LLM-Guided** — LLM selects most relevant children at each node
3. **Scoring Combination** — 70% LLM guidance + 30% keyword matching
4. **Confidence-Based** — Automatic fallback if confidence is low
5. **Production-Ready** — FastAPI, caching, error handling

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER REQUEST                               │
│                        (JSON Query)                                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  QUERY ANALYZER │
                    │   (analyzer.py) │
                    └────────┬────────┘
                             │
                    ┌────────▼─────────────┐
                    │ Extract Intent,      │
                    │ Keywords,            │
                    │ Domain               │
                    └────────┬─────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
    ┌──────────┐      ┌──────────┐      ┌──────────┐
    │  Intent  │      │ Keywords │      │  Domain  │
    └──────────┘      └──────────┘      └──────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                    ┌────────▼────────────┐
                    │  TREE NAVIGATOR    │
                    │  (navigator.py)    │
                    │                    │
                    │ DFS with LLM       │
                    │ guidance           │
                    │ max_depth = 5      │
                    └────────┬───────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    │                    ▼
    ┌─────────┐         ┌────▼────┐         ┌─────────┐
    │ LLM     │         │ Keyword │         │ Scoring │
    │ Score   │◄────────┤ Matching◄─────────│ Logic   │
    │ (70%)   │         │ (30%)   │         │         │
    └─────────┘         └────┬────┘         └─────────┘
        │                    │
        └────────────────────┼─────────────────────┐
                             │                     │
                    ┌────────▼───────┐             │
                    │ Best Child     │             │
                    │ Selected       │             │
                    └────────┬───────┘             │
                             │                     │
                    ┌────────▼───────────┐         │
                    │ Continue DFS?       │         │
                    │ depth < max_depth   │         │
                    └────┬──────────┬─────┘         │
                         │yes       │no             │
                         ▼          ▼               │
                    ┌─────────┐ ┌──────────┐        │
                    │ Loop    │ │ Best     │        │
                    │ again   │ │ Node     │        │
                    └─────────┘ │ Found    │        │
                                └────┬─────┘        │
                                     │              │
                    ┌────────────────┴──────────────┘
                    │
                    ▼
            ┌───────────────────┐
            │ Compute           │
            │ Confidence        │
            │ Score             │
            └────────┬──────────┘
                     │
                ┌────▼────┐
                │ Conf     │
                │ >= 0.4?  │
                └───┬──┬───┘
                    │  │
              YES ──┘  └── NO
                    │
                    ▼
    ┌────────────────────────────┐
    │ FALLBACK MECHANISM         │
    │ (if confidence < 0.4)      │
    │ Full tree keyword search   │
    └────────────┬───────────────┘
                 │
                 ▼
    ┌─────────────────────────────┐
    │ ANSWER GENERATOR            │
    │ (answer_generator.py)       │
    │                             │
    │ Generate natural language   │
    │ answer using LLM            │
    └──────────┬──────────────────┘
               │
               ▼
    ┌──────────────────────────────┐
    │ RESPONSE                      │
    │ {                             │
    │   "answer": "...",           │
    │   "path": [...],             │
    │   "confidence": 0.85,        │
    │   "latency_ms": 1234.5       │
    │ }                             │
    └──────────────────────────────┘
```

## Module Documentation

### 1. `llm.py` — LLM Abstraction Layer

**Purpose**: Unified interface to multiple LLM providers.

**Key Functions**:
- `call_ollama(prompt, model)` — Call local Ollama server
- `call_groq(prompt, model)` — Call Groq API
- `call_llm(prompt, provider, model)` — Unified interface
- `parse_json_response(text)` — Extract JSON from LLM response with fallback

**Features**:
- Automatic JSON extraction from LLM responses
- Error handling for connection issues
- Support for Ollama (local) and Groq (API)
- Graceful fallback for malformed JSON

**Configuration** (via environment variables):
```
LLM_PROVIDER=ollama|groq
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
GROQ_API_KEY=gsk_...
GROQ_MODEL=mixtral-8x7b-32768
```

### 2. `query_analyzer.py` — Query Analysis

**Purpose**: Extract structured information from user queries.

**Key Functions**:
- `analyze_query(query, provider, model)` — LLM-based analysis
  - Returns: `{intent, keywords, domain}`
- `extract_keywords_from_text(text)` — Heuristic fallback

**Intent Types**:
- "understand" — User wants to learn about a concept
- "compare" — Compare two or more things
- "troubleshoot" — Solve a problem
- "design" — Design a system
- "explain" — Get explanation

**Domains**:
- "databases", "networking", "security", "caching"
- "messaging", "scalability", "distributed-systems", "general"

**Example**:
```python
result = analyze_query("How does consistent hashing work?")
# Returns:
# {
#   "intent": "explain",
#   "keywords": ["consistent", "hashing", "distributed"],
#   "domain": "caching"
# }
```

### 3. `navigator.py` — Tree Navigation Engine

**Purpose**: Core DFS tree traversal logic with LLM guidance.

**Key Functions**:

#### `keyword_match_score(query_keywords, node) → float`
- Counts keyword overlap in node's keywords and content
- Returns normalized score 0-1
- Also checks for word boundaries in content

#### `llm_score_children(query, node_name, children, provider, model) → dict`
- Asks LLM to score top 2-3 relevant children
- Returns `{child_name: score}`
- Limits evaluation to top 10 children

#### `combine_scores(llm_scores, keywords, children, weights) → dict`
- Combines LLM (70%) + keyword (30%) scores
- Returns `{child_name: combined_score}`
- Weights are configurable

#### `navigate_tree(query, keywords, root, max_depth, ...) → dict`
- Main DFS traversal function
- Returns:
  ```python
  {
    "best_node": node_dict,
    "best_node_name": str,
    "path": [root → ... → best_node],
    "score": float (0-1),
    "depth": int
  }
  ```

#### `compute_confidence(score, depth) → float`
```
confidence = min(1.0, score + depth * 0.05)
```
- Base score gets +0.05 per level deeper
- Max 1.0

#### `full_tree_traversal(...) → tuple`
- Exhaustive keyword-based search (fallback)
- Returns: `(node, name, path, score)`

**Configuration**:
```python
max_depth = 5          # Don't go deeper than 5 levels
llm_weight = 0.7       # 70% from LLM
keyword_weight = 0.3   # 30% from keywords
confidence_threshold = 0.4  # Fallback if below 0.4
```

### 4. `answer_generator.py` — Answer Generation

**Purpose**: Generate natural language answers using LLM.

**Key Functions**:

#### `generate_answer(query, content, path, provider, model, max_length) → str`
- Takes best node's content + original query
- Asks LLM to generate answer
- Trims if too long
- Returns generated answer string

#### `generate_summary(content, max_length, provider, model) → str`
- Summarize long content using LLM
- For fallback when content is very long

#### `extract_excerpt(content, max_length) → str`
- Non-LLM excerpt extraction
- Fast, tries to end at sentence boundaries
- Used as fallback when LLM is slow

**Example**:
```python
answer = generate_answer(
    "How does consistent hashing work?",
    node_content="Consistent hashing maps keys and servers to...",
    path=["System Design", "Caching", "Consistent Hashing"],
    provider="ollama"
)
# Returns: "Consistent hashing is a distributed algorithm..."
```

### 5. `main.py` — FastAPI Server

**Purpose**: Production-ready REST API.

**Key Endpoints**:

#### POST `/query`
Request:
```json
{"query": "How does database sharding work?"}
```
Response:
```json
{
  "answer": "Database sharding is...",
  "path": ["System Design", "Databases", "Sharding"],
  "confidence": 0.87,
  "latency_ms": 1850.3
}
```

#### POST `/query/debug`
Same as `/query` but includes:
```json
{
  "traversal_path": [...],      // Full navigation path
  "raw_score": 0.82,            // Before confidence adjustment
  "depth": 2,                   // Depth of selected node
  "query_analysis": {           // Query extraction results
    "intent": "explain",
    "keywords": [...],
    "domain": "..."
  }
}
```

#### GET `/health`
```json
{
  "status": "ok",
  "kb_loaded": true,
  "provider": "ollama",
  "cache_size": 15
}
```

#### GET `/stats`
```json
{
  "cache_size": 15,
  "kb_loaded": true,
  "kb_size": {"nodes_at_level": 5, "max_depth": 4},
  "provider": "ollama"
}
```

#### POST `/cache/clear`
Clear query cache.

**Features**:
- In-memory query caching
- CORS support
- Error handling with proper HTTP codes
- Request/response validation via Pydantic

**Configuration** (via environment or code):
```python
KB_PATH = "data/kb/knowledge_base.json"
LLM_PROVIDER = "ollama"     # or "groq"
LLM_MODEL = None            # Uses default
DEBUG = False               # Enable traversal logging
```

### 6. `cli_test.py` — Command-Line Testing

**Purpose**: Test without running server.

**Usage**:
```bash
python backend/tests/cli_test.py "Your question?"
python backend/tests/cli_test.py "Your question?" --debug
python backend/tests/cli_test.py "Your question?" --provider groq
python backend/tests/cli_test.py "Your question?" --no-answer
```

**Options**:
- `--debug` — Show traversal path
- `--provider {ollama|groq}` — Which LLM to use
- `--model NAME` — Specific model to use
- `--no-answer` — Skip answer generation

### 7. `setup_check.py` — Setup Validation

**Purpose**: Verify installation and configuration.

**Checks**:
- Required files exist
- Dependencies installed
- Knowledge base valid
- Environment configured
- LLM connectivity
- Module imports

**Usage**:
```bash
python backend/tests/setup_check.py
```

### 8. `test_modules.py` — Unit Tests

**Purpose**: Test each module independently.

**Tests**:
- `test_llm_module()` — JSON parsing, LLM interface
- `test_query_analyzer()` — Query extraction
- `test_navigator()` — Scoring, tree traversal
- `test_answer_generator()` — Excerpt creation
- `test_main_fastapi()` — FastAPI app structure
- `test_integration()` — End-to-end minimal flow

**Usage**:
```bash
python backend/tests/test_modules.py
```

## Data Flow

### Complete Query Flow

```
1. User POST /query
   ↓
2. query_analyzer extracts intent, keywords, domain
   ↓
3. navigator.navigate_tree() performs DFS:
   - For each level:
     a. llm_score_children() asks LLM to score
     b. keyword_match_score() for keyword matching
     c. combine_scores() merges (70% + 30%)
     d. Select best child, recurse
   ↓
4. compute_confidence() decides if confident enough
   - If confidence < 0.4 → full_tree_traversal (keyword fallback)
   ↓
5. answer_generator.generate_answer():
   - Take node content + original query
   - Ask LLM to generate answer
   ↓
6. Return JSON response with answer, path, confidence, latency
```

## Knowledge Base Structure

```json
{
  "System Design": {
    "Category": {
      "Topic": {
        "keywords": ["keyword1", "keyword2"],
        "content": "Detailed explanation...",
        "related": ["Related Topic 1", "Related Topic 2"],
        "children": {
          "Subtopic": {
            "keywords": [...],
            "content": "...",
            "children": { ... }
          }
        }
      }
    }
  }
}
```

Each node can have:
- `keywords` — List of relevant terms
- `content` — Main content/explanation
- `related` — Related topic names
- `children` or `subtopics` — Child nodes

## Error Handling

| Scenario | Handling |
|----------|----------|
| Ollama not running | RuntimeError with helpful message |
| Invalid JSON from LLM | Fallback to empty dict, continue |
| KB not found | HTTPException 503 |
| Empty query | HTTPException 400 |
| LLM error | HTTPException 500 with details |
| No children at node | Stop traversal, use current best |

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Tree navigation | O(k * d) where k ~ 5 (branching), d ~ 3-5 (depth) |
| LLM calls per query | 2-5 (1 for query analysis, 1-4 for navigation) |
| Typical latency | 2-5 seconds (Ollama) or 1-2 seconds (Groq) |
| Cache hit latency | < 1ms |
| Memory usage | < 100MB (KB + connections) |
| Request throughput | 10-50 qps with single process |

## Scaling Strategies

1. **Horizontal** — Multiple FastAPI processes behind load balancer
2. **Caching** — Redis for distributed cache
3. **LLM** — Use Groq (API) instead of Ollama for better throughput
4. **Async** — Consider async/await for concurrent requests
5. **KB** — Split large KB into indexed segments

## Security Considerations

- **Input validation** — Pydantic models
- **Rate limiting** — Not implemented, add for production
- **Authentication** — Not implemented, add API keys if needed
- **HTTPS** — Configure in reverse proxy (nginx/traefik)
- **API Key rotation** — Use environment variables, rotate regularly

## Deployment

### Local Development
```bash
python backend/src/main.py
# Server at http://localhost:8000
```

### Production (Gunicorn)
```bash
gunicorn -w 4 -b 0.0.0.0:8000 backend.src.main:app
```

### Running the Server
```bash
python backend/src/main.py
# Server at http://localhost:8000
```

### Note on Containerization
Container deployment instructions were removed from the repository per project preference. If you need containerization later, consider using a managed inference provider for LLMs.

## Future Enhancements

1. **Async support** — Use async/await for concurrent LLM calls
2. **Distributed caching** — Redis
3. **Multi-language KB** — Support different languages
4. **Fine-tuning** — Customize scoring with user feedback
5. **Visualization** — Show traversal path in UI
6. **Analytics** — Track query patterns
7. **A/B testing** — Test different navigation strategies
8. **Reranking** — Re-score top candidates before final selection

---

**Built with ❤️ for system design interviews. No vectors needed.** 🚀
