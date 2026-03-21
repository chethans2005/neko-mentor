# QUICK START GUIDE

Get the Vectorless System Design Assistant running in 5 minutes.

## 1. Install Dependencies (1 min)

```bash
pip install -r requirements.txt
```

## 2. Choose Your LLM Provider

### Option A: Ollama (Recommended - Free, Local)

```bash
# 1. Download Ollama from https://ollama.ai
# 2. In terminal 1, start Ollama:
ollama serve

# 3. In terminal 2, pull a model:
ollama pull llama3.1
```

### Option B: Groq (Free API)

```bash
# 1. Get API key from https://console.groq.com
# 2. Set environment variable:
export GROQ_API_KEY=gsk_your_key_here
# (or add to .env file)
```

## 3. Test It

### Using CLI (No Server Needed)

```bash
python backend/tests/cli_test.py "How does database sharding work?"
```

**Output:**
```
Query: How does database sharding work?

Analysis:
  Intent: explain
  Keywords: database, sharding, distributed
  Domain: databases

Navigation Results:
  Best Node: Database_Sharding
  Raw Score: 0.87
  Depth: 2

Confidence: 0.94 (94%)

Path: System Design > Databases > Sharding

ANSWER:
-------
Database sharding is a distribution technique that splits data across 
multiple database instances...
```

### Using API Server (FastAPI)

```bash
# Terminal 1: Start the server
python backend/src/main.py

# Terminal 2: Test with curl
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the CAP theorem?"}'
```

**Response:**
```json
{
  "answer": "The CAP theorem states that distributed systems can provide...",
  "path": ["System Design", "Distributed Systems", "CAP Theorem"],
  "confidence": 0.92,
  "latency_ms": 1850.3
}
```

## 4. Verify Your Setup

```bash
python backend/tests/setup_check.py
```

This checks:
- ✓ All required files exist
- ✓ Dependencies installed
- ✓ Knowledge base valid
- ✓ Environment configured
- ✓ Modules importable

## 5. Common Queries to Try

```bash
python backend/tests/cli_test.py "How does consistent hashing work?"
python backend/tests/cli_test.py "What is load balancing?"
python backend/tests/cli_test.py "Explain the CAP theorem"
python backend/tests/cli_test.py "How does database indexing improve performance?"
python backend/tests/cli_test.py "What's the difference between SQL and NoSQL?"
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Failed to connect to Ollama" | Start Ollama: `ollama serve` |
| "GROQ_API_KEY not set" | Export key or add to `.env` (see `backend/config/.env.example`) |
| "KB file not found" | Ensure `shared/data/kb/knowledge_base.json` exists (or `data/kb/knowledge_base.json`) |
| "Module not found" | Run `pip install -r requirements.txt` |

## Next Steps

- **API Documentation**: Visit `http://localhost:8000/docs` (when server is running)
- **Debug Mode**: `python backend/tests/cli_test.py "..." --debug`
- **Custom KB**: Modify `shared/data/kb/knowledge_base.json` (or `data/kb/knowledge_base.json` as fallback)
- **Production**: Deploy FastAPI container using Docker

---

**That's it! You have a working tree-based LLM navigator with no vector DBs.** 🚀
