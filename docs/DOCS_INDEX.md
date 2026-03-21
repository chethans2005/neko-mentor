# Documentation Index

Quick reference to navigate all documentation for the Vectorless System Design Assistant Backend.

## Start Here 👇

### 1. **QUICKSTART.md** (5 min read)
   - Get running in 5 minutes
   - Choose Ollama or Groq
   - First test query
   - Troubleshooting quick fixes
   - **Start here if you want to dive in fast**

### 2. **IMPLEMENTATION_SUMMARY.md** (10 min read)
   - Overview of what was built
   - All 14 files and their purposes
   - Key features and algorithms
   - Next steps
   - **Read this to understand the complete implementation**

---

## Detailed Guides

### 3. **BACKEND_README.md** (30 min read)
   - Complete architecture overview
   - Setup & installation guide
   - Full API documentation with examples
   - CLI tool usage
   - Configuration options
   - Performance notes
   - Troubleshooting guide
   - **Comprehensive reference for developers**

### 4. **ARCHITECTURE.md** (45 min read)
   - System design and principles
   - Detailed architecture diagram
   - Complete module-by-module documentation
   - Data flow explanations
   - Knowledge base structure
   - Error handling strategies
   - Performance characteristics
   - Scaling strategies
   - **In-depth technical reference**

### 5. **Deployment Guidance** (10 min read)
  - Run server directly: `python backend/src/main.py`
  - Configure `LLM_PROVIDER` and `GROQ_API_KEY` for cloud LLMs
  - For scalable production, use a managed inference provider and standard deployment tooling

---

## Code & Tools

### Testing & Validation

- **`setup_check.py`** — Validate your installation
  ```bash
    python backend/tests/setup_check.py
  ```

- **`test_modules.py`** — Run unit tests
  ```bash
  python backend/tests/test_modules.py
  ```

- **`cli_test.py`** — Test without server
  ```bash
  python backend/tests/cli_test.py "Your question?"
  python backend/tests/cli_test.py "Your question?" --debug
  ```

### Configuration

- **`.env.example`** — Environment variable template
  ```bash
  cp backend/config/.env.example backend/config/.env
  # Edit .env with your settings
  ```

- **`requirements.txt`** — Python dependencies
  ```bash
  pip install -r requirements.txt
  ```

---

## Core Modules

### Backend Implementation

**5 Core Modules** (~1,500 lines total):

1. **`llm.py`** — LLM abstraction (Ollama + Groq)
2. **`query_analyzer.py`** — Query intent extraction
3. **`navigator.py`** — Tree navigation engine
4. **`answer_generator.py`** — Answer generation
5. **`main.py`** — FastAPI server

**See ARCHITECTURE.md for detailed module documentation**

---

## Quick Reference

### Running the System

```bash
# CLI (no server)
python backend/tests/cli_test.py "Your question?"

# FastAPI Server
python backend/src/main.py
# Then: curl -X POST http://localhost:8000/query \
#   -H "Content-Type: application/json" \
#   -d '{"query": "Your question?"}'

# Run server
python backend/src/main.py
```

### Common Tasks

| Task | Command |
|------|---------|
| Verify setup | `python backend/tests/setup_check.py` |
| Run tests | `python backend/tests/test_modules.py` |
| Test CLI | `python backend/tests/cli_test.py "question?"` |
| Debug mode | `python backend/tests/cli_test.py "question?" --debug` |
| Start server | `python backend/src/main.py` |
| Clear cache | `curl -X POST http://localhost:8000/cache/clear` |

### Configuration

| Setting | File | Environment |
|---------|------|-------------|
| LLM Provider | `backend/config/.env.example` | `LLM_PROVIDER` |
| Ollama URL | `backend/config/.env.example` | `OLLAMA_BASE_URL` |
| Ollama Model | `backend/config/.env.example` | `OLLAMA_MODEL` |
| Groq API Key | `backend/config/.env.example` | `GROQ_API_KEY` |
| Debug Mode | `main.py:DEBUG` | — |

---

## Learning Path

### For Quick Testing (15 minutes)
1. Read: **QUICKSTART.md**
2. Run: `python backend/tests/setup_check.py`
3. Try: `python backend/tests/cli_test.py "How does caching work?"`

### For Development (1 hour)
1. Read: **IMPLEMENTATION_SUMMARY.md**
2. Read: **BACKEND_README.md** (API section)
3. Run: `python backend/tests/test_modules.py`
4. Read: **ARCHITECTURE.md** (Modules section)
5. Explore: Code in each module

### For Production Deployment (2 hours)
1. Read: **QUICKSTART.md**
2. Read: **BACKEND_README.md** (Setup section)
3. Configure `.env`
4. Run: `python backend/tests/setup_check.py`
5. Deploy: `python backend/src/main.py`

### For Deep Understanding (4 hours)
1. Read: **IMPLEMENTATION_SUMMARY.md**
2. Read: **ARCHITECTURE.md** (entire file)
3. Run: `python backend/tests/test_modules.py` with debugging
4. Trace through: `python backend/tests/cli_test.py --debug` for a query
5. Review: Each module's code with comments

---

## API Quick Reference

### POST `/query`
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "How does database sharding work?"}'
```
Returns: `{answer, path, confidence, latency_ms}`

### POST `/query/debug`
Same as `/query` but with: `traversal_path, raw_score, depth, query_analysis`

### GET `/health`
```bash
curl "http://localhost:8000/health"
```
Returns: `{status, kb_loaded, provider, cache_size}`

### GET `/stats`
```bash
curl "http://localhost:8000/stats"
```
Returns: `{cache_size, kb_loaded, kb_size, provider}`

### POST `/cache/clear`
```bash
curl -X POST "http://localhost:8000/cache/clear"
```
Returns: `{cleared}`

---

## Troubleshooting

**Problem** → **Solution** → **Reference**

- Can't run setup → Wrong directory → QUICKSTART.md
- Missing dependencies → `pip install -r requirements.txt` → QUICKSTART.md
- "Failed to connect to Ollama" → Start Ollama: `ollama serve` → QUICKSTART.md
- GROQ_API_KEY error → Set in .env or environment → QUICKSTART.md
- API returns 503 → KB not loaded, check KB_PATH → BACKEND_README.md
- Slow first query → Normal, LLM loading time → ARCHITECTURE.md
- Debug navigation → Use `--debug` flag → CLI_TEST.py
- Complete confusion → Start with IMPLEMENTATION_SUMMARY.md

---

## File Structure

```
vectorless/
├── Core Modules
│   ├── llm.py                      # LLM abstraction
│   ├── query_analyzer.py           # Query analysis
│   ├── navigator.py                # Tree navigation
│   ├── answer_generator.py         # Answer generation
│   └── main.py                     # FastAPI server
│
├── Testing & Validation
│   ├── setup_check.py              # Setup verification
│   ├── test_modules.py             # Unit tests
│   └── cli_test.py                 # CLI testing tool
│
├── Configuration
│   ├── requirements.txt            # Dependencies
│   ├── .env.example                # Environment template
│   └── Dockerfile                  # (optional)
│
├── Documentation
│   ├── QUICKSTART.md               # (YOU ARE HERE)
│   ├── IMPLEMENTATION_SUMMARY.md   # Overview
│   ├── BACKEND_README.md           # Complete reference
│   ├── ARCHITECTURE.md             # Deep dive
 │   ├── DOCKER.md                   # Deployment (deprecated)
│   └── README.md                   # Original README
│
└── Data
    └── data/kb/
        └── knowledge_base.json     # Hierarchical KB
```

---

## Support & Help

### Documentation
- **Fast questions?** → QUICKSTART.md
- **API help?** → BACKEND_README.md (API section)
- **Architecture questions?** → ARCHITECTURE.md
- **Deployment?** → Run `python backend/src/main.py` (no Docker)
- **Overall understanding?** → IMPLEMENTATION_SUMMARY.md

- ### Tools
- **Something broken?** → Run `python backend/tests/setup_check.py`
- **Code questions?** → Run `python backend/tests/test_modules.py`
- **Debug mode?** → Use `python backend/tests/cli_test.py "query" --debug`
- **API testing?** → Use `/query/debug` endpoint

### Common Issues
- See "Troubleshooting" section above
- Check QUICKSTART.md
- Run setup_check.py to diagnose

---

## Environment Setup Checklist

- [ ] Python 3.10+ installed
- [ ] Dependencies: `pip install -r requirements.txt`
 - [ ] Copy `backend/config/.env.example` to `backend/config/.env`
- [ ] Choose provider: Ollama OR Groq
- [ ] If Ollama: `ollama serve` running with `ollama pull llama3.1`
- [ ] If Groq: `GROQ_API_KEY` set in `.env`
- [ ] Run: `python backend/tests/setup_check.py` → All green ✓
- [ ] Test: `python backend/tests/cli_test.py "Your question?"` → Works!

---

## Next Steps

**Pick your path:**

1. **I want to get started now** → Read QUICKSTART.md (5 min)
2. **I want to understand everything** → Read IMPLEMENTATION_SUMMARY.md (10 min)
3. **I want to use the API** → Read BACKEND_README.md API section (10 min)
4. **I want to deploy** → Run the server directly: `python backend/src/main.py` (no Docker)
5. **I want to understand the code** → Read ARCHITECTURE.md (45 min)

---

**Happy navigating! 🚀**

*No vectors needed. Just pure tree traversal + LLM reasoning.*
