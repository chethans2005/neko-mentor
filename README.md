# Vectorless System Design Assistant

A chatbot that answers system design questions by **navigating a hierarchical knowledge tree** — no vector DB, no embeddings. The LLM acts as a navigator, choosing the best node at each level.

## Architecture

```
User Query
    │
    ▼
┌─────────────┐    ┌──────────────────────────────────┐
│  FastAPI    │───▶│         Navigator                 │
│  (main.py)  │    │  1. Get children of current node  │
└─────────────┘    │  2. Ask LLM: "which child?"       │
                   │  3. Move into chosen child        │
                   │  4. Repeat until leaf or depth    │
                   └──────────────┬───────────────────┘
                                  │
                        ┌─────────▼──────────┐
                        │    LLM Client       │
                        │  (OpenAI / Ollama)  │
                        └─────────────────────┘

Response:
{
  "answer": "Consistent hashing maps both nodes and keys...",
  "path": ["System Design", "Components", "Load Balancing", "Consistent Hashing"],
  "confidence": 0.91,
  "latency_ms": 320.5
}
```

## Project Structure

```
├── knowledge_base.json   # Hierarchical system design KB
├── navigator.py          # Core tree traversal logic
├── llm_client.py         # LLM abstraction (OpenAI / Ollama)
├── main.py               # FastAPI server
├── cli.py                # Quick CLI testing
└── requirements.txt
```

## Setup

```bash
pip install -r requirements.txt

# For OpenAI:
export OPENAI_API_KEY="sk-..."

# For Ollama (local):
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=llama3
ollama pull llama3
```

## Run

```bash
# Start server
uvicorn main:app --reload

# CLI test
python cli.py "How does consistent hashing work?"
python cli.py "What is the difference between Kafka and RabbitMQ?"
python cli.py "Design a URL shortener"
```

## API

### `POST /ask`
```json
{
  "query": "How does consistent hashing work?",
  "max_depth": 5
}
```

Response:
```json
{
  "answer": "Consistent hashing minimizes key remapping...",
  "path": ["System Design", "Components", "Load Balancing", "Consistent Hashing"],
  "confidence": 0.91,
  "latency_ms": 312.4
}
```

### `GET /topics`
Lists all categories and topics in the KB.

### `POST /cache/clear`
Clears the in-memory LLM response cache.

## How Navigation Works

At each tree level, the navigator:
1. Extracts navigable children (sub-categories and subtopics)
2. Sends a structured prompt to the LLM: "Given the query and these options, which is most relevant?"
3. LLM returns `CHOICE: <name>` and `CONFIDENCE: <0-1>`
4. If confidence ≥ 0.85 or we reach a leaf, we stop
5. If no good match found, falls back to keyword overlap search

## Extending the Knowledge Base

The KB is a nested JSON. Add new topics like this:

```json
{
  "System Design": {
    "Components": {
      "Your New Topic": {
        "keywords": ["keyword1", "keyword2"],
        "content": "Full explanation here...",
        "related": ["Related Topic 1"],
        "subtopics": {
          "Subtopic Name": {
            "keywords": ["..."],
            "content": "..."
          }
        }
      }
    }
  }
}
```

## Coverage (Knowledge Base)

| Category | Topics |
|----------|--------|
| Fundamentals | Scalability, Reliability, CAP Theorem, Latency vs Throughput |
| Components | Load Balancing, Caching (Redis, CDN, Invalidation), Message Queues (Kafka), Databases (Sharding, Replication, Indexing, ACID), API Design, Storage |
| Distributed Systems | Consensus (Raft/Paxos), Distributed Transactions (2PC, Saga), Service Discovery |
| Architectural Patterns | Microservices, Service Mesh, API Gateway, Event-Driven, CQRS, Event Sourcing |
| Real-World Systems | URL Shortener, Rate Limiter, Notification System, Chat System, Search Autocomplete |
| Security | Auth (JWT, OAuth, RBAC), Data Security |
| Observability | Monitoring, Distributed Tracing |
