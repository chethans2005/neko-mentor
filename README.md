# Vectorless System Design Assistant

A tree-based knowledge base navigation system with LLM guidance for system design questions. No vector embeddings required.

## Quick Start

```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Check setup
python backend/tests/setup_check.py

# 3. Test with CLI (no server needed)
python backend/tests/cli_test.py "How does consistent hashing work?"

# 4. Run FastAPI server
python backend/src/main.py

# 5. Query the API
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is a load balancer?"}'
```

## Project Structure

```
vectorless/
├── backend/                      # Backend implementation
│   ├── src/                      # Core modules
│   │   ├── llm.py               # LLM abstraction (Ollama/Groq)
│   │   ├── query_analyzer.py    # Query parsing and analysis
│   │   ├── navigator.py         # Tree-based KB navigation
│   │   ├── answer_generator.py  # Answer generation
│   │   └── main.py              # FastAPI server
│   ├── tests/                   # Testing and validation
│   │   ├── cli_test.py          # CLI testing tool
│   │   ├── setup_check.py       # Environment validation
│   │   └── test_modules.py      # Unit tests
│   ├── config/                  # Configuration files
│   │   └── .env.example         # Environment template
│   └── requirements.txt         # Python dependencies
│
├── frontend/                     # Frontend placeholder
│   └── README.md               # Frontend setup instructions
│
├── docs/                        # Documentation
│   ├── START_HERE.md           # 3-min quick overview
│   ├── QUICKSTART.md           # 5-min setup
│   ├── GETTING_STARTED.md      # Complete checklist
│   ├── BACKEND_README.md       # Full API reference
│   ├── ARCHITECTURE.md         # Technical details
│   ├── IMPLEMENTATION_SUMMARY.md
│   ├── DOCKER.md              # Docker deployment (removed)
│   ├── DOCS_INDEX.md          # Documentation index
│   ├── DELIVERY_SUMMARY.md    # Project summary
│   └── README.md              # Documentation home
│
├── data/                       # Data files
│   └── kb/                    # Knowledge base
│       ├── knowledge_base.json  # Hierarchical KB (100+ system design topics)
│       └── *.raw.txt          # Raw topic files
│
├── shared/                     # Shared resources
│   └── data/kb/               # Alternative KB location
│
├── requirements.txt           # Root dependencies (for convenience)
└── README.md                  # This file
```

## Documentation

Start with the **docs/** folder:

1. **[docs/START_HERE.md](docs/START_HERE.md)** (3 min) — Quick overview
2. **[docs/QUICKSTART.md](docs/QUICKSTART.md)** (5 min) — Installation and first query
3. **[docs/BACKEND_README.md](docs/BACKEND_README.md)** (30 min) — Complete reference
4. **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** (45 min) — Technical deep dive

## Features

- **Tree-Based Navigation**: Hierarchical knowledge base instead of flat vector search
- **LLM-Guided Scoring**: 70% LLM + 30% keyword matching for node selection
- **Multi-Provider LLM Support**: Ollama (local) and Groq (API)
- **Query Caching**: In-memory response caching for performance
- **FastAPI Server**: REST API with comprehensive endpoints
- **Testing Tools**: CLI test, setup validator, and unit tests
 - **No Docker Required**: Run the server directly without Docker

## How It Works
│   ├── (no Docker)            # Docker removed per user preference
The assistant uses DFS tree traversal:

1. **Query Analysis** → Extract intent, keywords, domain
2. **Tree Navigation** → DFS with LLM-guided child selection
3. **Node Scoring** → Combined LLM (70%) + keyword (30%) scores
4. **Answer Generation** → LLM-based response from selected node

Maximum depth: 5 levels. Confidence score: base_score + depth × 0.05 (capped at 1.0)

## LLM Providers

### Ollama (Local)
Best for development/testing. Free, no API key needed.

```bash
# Install and run Ollama
ollama pull llama3.1
ollama serve
```

Set environment:
```bash
export LLM_PROVIDER=ollama
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=llama3.1
```

### Groq (Cloud)
Best for production. Free tier available.

```bash
# Get API key from https://console.groq.com
export LLM_PROVIDER=groq
- **No Docker Required**: Run the server directly without Docker
export GROQ_MODEL=mixtral-8x7b-32768
```

## Testing

### Setup Validation
```bash
python backend/tests/setup_check.py
```

### CLI Testing
```bash
# Simple query
python backend/tests/cli_test.py "What is consistent hashing?"

# With debug info
python backend/tests/cli_test.py "What is CAP theorem?" --debug

# Using Groq
python backend/tests/cli_test.py "Question" --provider groq
```

### Run Unit Tests
```bash
python backend/tests/test_modules.py
```

## API Endpoints

### Main Query Endpoint
```
POST /query
{
  "query": "How does load balancing work?",
  "provider": "ollama",
  "use_debug": false
}
```

### Get Stats
```
GET /stats
```

### Health Check
```
GET /health
```

See [docs/BACKEND_README.md](docs/BACKEND_README.md) for complete API documentation.

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp backend/config/.env.example .env
```

Key variables:
- `LLM_PROVIDER` — "ollama" or "groq"
- `OLLAMA_BASE_URL` — Ollama server URL (default: http://localhost:11434)
- `GROQ_API_KEY` — Groq API key
- `KB_PATH` — Path to knowledge base JSON
- `HOST` — Server host (default: 127.0.0.1)
- `PORT` — Server port (default: 8000)

## Installation

### Requirements
- Python 3.10+
- pip
- Ollama or Groq API key (for LLM)

### Steps
```bash
# 1. Clone or download the project
cd vectorless

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Verify setup
python backend/tests/setup_check.py

# 4. Start using it
python backend/tests/cli_test.py "Your question"
```

## Deployment (no Docker)

Run the FastAPI server directly:

```bash
python backend/src/main.py
```

Or use the CLI for quick queries:

```bash
python backend/tests/cli_test.py "Your question"
```

## Knowledge Base

The knowledge base is located at `data/kb/knowledge_base.json` and contains 100+ system design topics including:

- Databases (SQL, NoSQL, indexing, sharding)
- Caching (Redis, Memcached, consistent hashing)
- Networking (DNS, load balancing, CDN)
- Distributed Systems (consensus, replication, Paxos)
- Security (JWT, OAuth, API keys)
- And more...

Each topic is structured hierarchically with content, keywords, and related topics.

## Troubleshooting

### "Ollama not running"
```bash
ollama serve
```

### "KB not found"
Ensure `data/kb/knowledge_base.json` exists or set `KB_PATH` environment variable.

### Deployment

Run the FastAPI server directly (no Docker required):

```bash
python backend/src/main.py
```
For CLI testing or scripting, use the `backend/tests` scripts. See `docs/GETTING_STARTED.md` for options.
3. Query the API: `curl http://localhost:8000/query`
4. Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for technical details
5. Build a frontend (see [frontend/README.md](frontend/README.md))

## Contributing

To add new system design topics:

1. Create a new `.raw.txt` file in `data/raw/`
2. Build the knowledge base: `python data/kb/build_kb_local.py`
3. Test queries: `python backend/tests/cli_test.py "Your new topic"`

## License

See LICENSE file for details.

## Questions?

- Start with [docs/START_HERE.md](docs/START_HERE.md)
- Full reference: [docs/BACKEND_README.md](docs/BACKEND_README.md)
- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
