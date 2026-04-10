# Vectorless System Design Assistant

A high-performance backend that answers system design questions by **navigating a hierarchical knowledge tree** using LLM guidance—**without vector embeddings, FAISS, or any vector databases**.

## Features

✅ **Tree-based retrieval** — Efficient hierarchical knowledge base navigation  
✅ **LLM-guided scoring** — Uses LLM to select most relevant children at each level  
✅ **Keyword matching** — Fallback scoring based on keyword overlap (30% weight)  
✅ **Confidence scoring** — Computes confidence based on traversal depth and match quality  
✅ **Automatic fallback** — Full tree traversal if confidence < 0.4  
✅ **Multi-provider LLM support** — Ollama (local) or Groq (API)  
✅ **Query caching** — In-memory cache for frequent queries  
✅ **FastAPI server** — Production-ready REST API  
✅ **CLI tool** — Command-line testing without server  
✅ **Debug mode** — Detailed traversal logging and statistics  

## Architecture

```
User Query
    │
    ▼
┌──────────────────┐
│ Query Analyzer   │  ← Extract intent, keywords, domain
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Tree Navigator  │  ← DFS with LLM guidance
│                  │     1. Ask LLM: "which child?"
│ max_depth = 5    │     2. Score with: LLM (70%) + keyword (30%)
└────────┬─────────┘
         │
         ▼
  ┌─────────────────┐
```
├── backend/src/main.py                    # FastAPI server
├── backend/src/llm.py                     # LLM abstraction (Ollama + Groq)
├── backend/src/query_analyzer.py          # Query intent/keyword extraction
├── backend/src/navigator.py               # Tree traversal + scoring
├── backend/src/answer_generator.py        # Answer generation
├── backend/tests/cli_test.py              # CLI testing tool
├── requirements.txt                       # Python dependencies
├── backend/config/.env.example            # Environment variables template
├── shared/data/kb/
│   └── knowledge_base.json                # Hierarchical KB (preferred)
└── README.md                              # This file
```
  │ Confidence?     │
  └────┬───────────┬┘
    <0.4 >= 0.4
      │     │
Copy `backend/config/.env.example` to `.env` and configure:
      │  Use best node
      │     │
cp backend/config/.env.example .env
  Full   Answer
  Tree   Generator
  Traverse
      │     │
      └──┬──┘
python backend/src/main.py
    ┌─────────────┐
    │  LLM Call   │  ← Generate answer
    └──────┬──────┘
           ▼
       Response JSON
```

## Project Structure
python backend/tests/cli_test.py "How does database sharding work?"
```
├── main.py                    # FastAPI server
├── llm.py                     # LLM abstraction (Ollama + Groq)
├── query_analyzer.py          # Query intent/keyword extraction
├── navigator.py               # Tree traversal + scoring
├── answer_generator.py        # Answer generation
1. Create `shared/data/kb/custom_kb.json` (or `data/kb/custom_kb.json`) with the same hierarchical structure
├── cli_test.py                # CLI testing tool
  ```python
  KB_PATH = Path("shared/data/kb/custom_kb.json")
  ```
│   └── kb/
│       └── knowledge_base.json   # Hierarchical KB
└── README.md                  # This file
```

## Setup & Installation

### 1. Prerequisites

- **Python 3.10+**
- **Ollama** (if using local LLM) — download from [ollama.ai](https://ollama.ai)
- Or **Groq API key** (if using cloud LLM) — get from [console.groq.com](https://console.groq.com)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp backend/config/.env.example backend/config/.env
```

**For Ollama (local, free):**
```
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1
OLLAMA_BASE_URL=http://localhost:11434
```

**For Groq (API, free tier available):**
```
LLM_PROVIDER=groq
# Set your real key in `backend/config/.env` (do not commit it)
GROQ_API_KEY=GROQ_YOUR_KEY
GROQ_MODEL=mixtral-8x7b-32768
```

### 4. Start Ollama (if using local LLM)

```bash
ollama serve
# In another terminal:
ollama pull llama3.1
```

## Usage

### Option A: FastAPI Server

```bash
# Start the server
python backend/src/main.py
# Server runs on http://localhost:8000
```

**API Endpoints:**

#### POST `/query`
Answer a system design question.

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "How does consistent hashing work?"}'
```

**Response:**
```json
{
  "answer": "Consistent hashing is a distributed algorithm...",
  "path": ["System Design", "Caching", "Consistent Hashing"],
  "confidence": 0.85,
  "latency_ms": 2340.5
}
```

#### POST `/query/debug`
Same as `/query` but with additional debugging information.

```bash
curl -X POST "http://localhost:8000/query/debug" \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain the CAP theorem"}'
```

**Response:**
```json
{
  "answer": "...",
  "path": ["System Design", "..."],
  "confidence": 0.82,
  "latency_ms": 1850.3,
  "traversal_path": ["System Design", "Distributed Systems", "CAP Theorem"],
  "raw_score": 0.78,
  "depth": 2,
  "query_analysis": {
    "intent": "explain",
    "keywords": ["CAP", "theorem", "consistency"],
    "domain": "distributed-systems"
  }
}
```

#### GET `/health`
Health check.

```bash
curl "http://localhost:8000/health"
```

#### GET `/stats`
Get cache and KB statistics.

```bash
curl "http://localhost:8000/stats"
```

#### POST `/cache/clear`
Clear query cache.

```bash
curl -X POST "http://localhost:8000/cache/clear"
```

### Option B: CLI Tool

Test without starting a server:

```bash
# Basic query
python backend/tests/cli_test.py "How does database sharding work?"

# With debug output
python backend/tests/cli_test.py "What is consistent hashing?" --debug

# Using Groq instead of Ollama
python backend/tests/cli_test.py "Explain the CAP theorem" --provider groq

# Skip answer generation (just show traversal)
python backend/tests/cli_test.py "What is load balancing?" --no-answer
```

## How It Works

### 1. Query Analysis
The query is sent to the LLM to extract:
- **Intent** — "understand", "compare", "troubleshoot", "design", "explain"
- **Keywords** — Relevant technical terms
- **Domain** — "databases", "networking", "security", etc.

### 2. Tree Navigation (DFS)
Starting from the root ("System Design"):
1. Get children of current node
2. Ask LLM: "Which 2-3 children are most relevant to this query?"
3. Compute combined score: 70% LLM + 30% keyword matching
4. Navigate to best child
5. Repeat until max depth (5 levels) or leaf node reached

### 3. Scoring
For each child:
```
combined_score = 0.7 * llm_score + 0.3 * keyword_match_score
```

**Keyword Match Score:**
- Counts how many query keywords appear in node's keywords/content
- Normalized to 0-1 range

### 4. Confidence Calculation
```
confidence = min(1.0, score + depth * 0.05)
```
- Base score from navigation
- +0.05 boost per level deep (reward going deeper)
- Capped at 1.0

### 5. Fallback Mechanism
If confidence < 0.4:
- Perform full tree traversal
- Score every node by keyword matching only
- Pick node with highest keyword score

### 6. Answer Generation
Selected node's content + original query sent to LLM to generate a natural language answer.

## Configuration

### Performance Tuning

**`navigator.py`:**
- `max_depth` — Maximum traversal depth (default: 5)
- `llm_weight` / `keyword_weight` — Score combination weights
- `confidence_threshold` — Triggers fallback (default: 0.4)

**`main.py`:**
- `LLM_PROVIDER` — "ollama" (free, local) or "groq" (API)
- `DEBUG` — Enable traversal logging

### Knowledge Base Structure

The KB is a hierarchical JSON:
```json
{
  "System Design": {
    "Caching": {
      "Invalidation": {
        "keywords": ["cache", "invalidation", "TTL"],
        "content": "...",
        "related": ["Memory Management", "Performance"],
        "children": { ... }
      }
    }
  }
}
```

Each node has:
- `keywords` — List of relevant terms
- `content` — Detailed explanation
- `related` — Related topics
- `children` / `subtopics` — Child nodes

## Examples

### Example 1: Basic Query
```bash
$ python backend/tests/cli_test.py "How does consistent hashing work?"

Query: How does consistent hashing work?

Analysis:
  Intent: explain
  Keywords: consistent, hashing, distributed
  Domain: caching

Navigation Results:
  Best Node: Consistent Hashing
  Raw Score: 0.82
  Depth: 2
  Time: 1.34s

Confidence: 0.89 (89%)

Path: System Design > Caching > Consistent Hashing

ANSWER:
-------
Consistent hashing is a distributed algorithm that maps both keys and 
servers to points on a hash ring. Each key is stored on the server whose 
hash value is nearest to it on the ring. When a server is added or removed,
only a fraction of keys need to be rehashed, making it ideal for caching
and distributed storage systems...
```

### Example 2: Using Groq API
```bash
$ python backend/tests/cli_test.py "Explain the CAP theorem" --provider groq

Query: Explain the CAP theorem

Analysis:
  Intent: explain
  Keywords: CAP, consistency, availability
  Domain: distributed-systems

Navigation Results:
  Best Node: CAP Theorem
  Raw Score: 0.91
  Depth: 2

Confidence: 0.96 (96%)

ANSWER:
-------
The CAP theorem states that a distributed system can provide at most 
two out of three guarantees...
```

### Example 3: Debug Mode
```bash
$ python backend/tests/cli_test.py "Database sharding" --debug
```

[DEBUG] Loading knowledge base...
[DEBUG] Analyzing query...
[DEBUG] Navigating knowledge base...
  Depth 0: System Design -> Components (score: 0.76)
  Depth 1: Components -> Database (score: 0.82)
  Depth 2: Database -> Sharding (score: 0.89)

Confidence: 0.94

...
```

## Performance Notes

- **First query**: 2-5 seconds (depends on LLM latency)
- **Cached queries**: < 1ms
- **No vector search overhead** — Tree traversal is O(k * d) where k is branching factor (~5) and d is depth (~3-5)
- **Memory usage**: < 100MB (KB + LLM connection)

## Advanced: Custom Knowledge Base

To use a different KB:

1. Create `shared/data/kb/custom_kb.json` (or `data/kb/custom_kb.json`) with the same hierarchical structure
2. Update `KB_PATH` in `backend/src/main.py` if needed:
  ```python
  KB_PATH = Path("shared/data/kb/custom_kb.json")
  ```

## Limitations & Tradeoffs

**Advantages:**
- No vector DB required
- Fast, lightweight, local-first
- Easy to debug (transparent traversal)
- Works offline with Ollama

**Tradeoffs:**
- Tree depth must be reasonable (deep trees hurt performance)
- Keyword matching is simple (no semantic understanding)
- Requires well-structured hierarchical KB
- Max depth limits how specific answers can be

## API Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (e.g., empty query) |
| 500 | Server error (LLM unavailable, parse error, etc.) |
| 503 | Service unavailable (KB not loaded) |

## Troubleshooting

### "Failed to connect to Ollama"
- Make sure Ollama is running: `ollama serve`
- Check `OLLAMA_BASE_URL` in `.env`

### "GROQ_API_KEY environment variable not set"
- Set `GROQ_API_KEY` in `.env` or terminal
- Get key from https://console.groq.com

### "Knowledge base not loaded"
- Ensure `shared/data/kb/knowledge_base.json` (or `data/kb/knowledge_base.json`) exists
- Check file path in `backend/src/main.py`

### Low confidence scores
- May indicate KB doesn't cover query topic well
- Try broader queries
- Check query analysis: `python backend/tests/cli_test.py "..." --debug`

### Slow responses
- First LLM response is slower due to model loading
- Use provider="groq" for faster API responses
- Reduce `max_depth` in navigator.py

## License

MIT

## References

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Ollama](https://ollama.ai/)
- [Groq API](https://console.groq.com/)
- [System Design Interview Resources](https://github.com/topics/system-design)

---

**Built with ❤️ for system design interviews**
