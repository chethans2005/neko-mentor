"""
generate_kb_ollama.py — Generate knowledge_base.json from a topic list using local Ollama.

Usage:
    ollama pull llama3.1          # pull model first
    python generate_kb_ollama.py  # generates knowledge_base.json
    python generate_kb_ollama.py --model mistral --merge
    python generate_kb_ollama.py --dry-run   # test without calling Ollama
"""

import json
import re
import time
import argparse
import urllib.request
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
OLLAMA_URL    = "http://localhost:11434/api/generate"
OLLAMA_MODEL  = "llama3.1"
OUTPUT_FILE   = "data/kb/knowledge_base.json"
PROGRESS_FILE = "data/progress/ollama_progress.json"
DELAY_SECONDS = 0.5   # Ollama is local, no rate limit needed — small delay to avoid overload

# ── Full topic hierarchy ───────────────────────────────────────────────────────
TOPICS = [
    # (category, topic, parent_topic_or_None)
    ("Fundamentals",              "Scalability",                        None),
    ("Fundamentals",              "Vertical Scaling",                   "Scalability"),
    ("Fundamentals",              "Horizontal Scaling",                 "Scalability"),
    ("Fundamentals",              "Auto Scaling",                       "Scalability"),
    ("Fundamentals",              "Reliability and Availability",       None),
    ("Fundamentals",              "Fault Tolerance",                    "Reliability and Availability"),
    ("Fundamentals",              "Graceful Degradation",               "Reliability and Availability"),
    ("Fundamentals",              "Chaos Engineering",                  "Reliability and Availability"),
    ("Fundamentals",              "CAP Theorem",                        None),
    ("Fundamentals",              "Consistency Models",                 "CAP Theorem"),
    ("Fundamentals",              "PACELC Theorem",                     "CAP Theorem"),
    ("Fundamentals",              "Latency vs Throughput",              None),
    ("Fundamentals",              "Back-of-Envelope Estimation",        None),
    ("Fundamentals",              "Latency Numbers Every Engineer Knows","Back-of-Envelope Estimation"),

    ("Networking",                "DNS",                                None),
    ("Networking",                "DNS Resolution Flow",                "DNS"),
    ("Networking",                "HTTP and HTTPS",                     None),
    ("Networking",                "HTTP2 vs HTTP3",                     "HTTP and HTTPS"),
    ("Networking",                "TLS SSL Handshake",                  "HTTP and HTTPS"),
    ("Networking",                "TCP vs UDP",                         None),
    ("Networking",                "WebSockets",                         None),
    ("Networking",                "Long Polling vs SSE vs WebSockets",  None),
    ("Networking",                "CDN",                                None),
    ("Networking",                "Push vs Pull CDN",                   "CDN"),
    ("Networking",                "Edge Computing",                     "CDN"),

    ("Components",                "Load Balancing",                     None),
    ("Components",                "L4 vs L7 Load Balancer",            "Load Balancing"),
    ("Components",                "Load Balancing Algorithms",         "Load Balancing"),
    ("Components",                "Consistent Hashing",                "Load Balancing"),
    ("Components",                "Reverse Proxy",                     "Load Balancing"),
    ("Components",                "Caching",                            None),
    ("Components",                "Cache Strategies",                   "Caching"),
    ("Components",                "Cache Eviction Policies",            "Caching"),
    ("Components",                "Cache Invalidation",                 "Caching"),
    ("Components",                "Cache Stampede",                     "Caching"),
    ("Components",                "Redis vs Memcached",                 "Caching"),
    ("Components",                "Databases",                          None),
    ("Components",                "SQL vs NoSQL",                       "Databases"),
    ("Components",                "ACID Transactions",                  "Databases"),
    ("Components",                "Database Indexing",                  "Databases"),
    ("Components",                "B-Tree Index",                       "Database Indexing"),
    ("Components",                "LSM Tree",                           "Database Indexing"),
    ("Components",                "Inverted Index",                     "Database Indexing"),
    ("Components",                "Database Sharding",                  "Databases"),
    ("Components",                "Database Replication",               "Databases"),
    ("Components",                "Single Leader Replication",          "Database Replication"),
    ("Components",                "Multi Leader Replication",           "Database Replication"),
    ("Components",                "Leaderless Replication",             "Database Replication"),
    ("Components",                "Connection Pooling",                 "Databases"),
    ("Components",                "Query Optimization",                 "Databases"),
    ("Components",                "Message Queues",                     None),
    ("Components",                "Apache Kafka",                       "Message Queues"),
    ("Components",                "Kafka Topics and Partitions",        "Apache Kafka"),
    ("Components",                "Kafka Consumer Groups",              "Apache Kafka"),
    ("Components",                "RabbitMQ",                           "Message Queues"),
    ("Components",                "Dead Letter Queue",                  "Message Queues"),
    ("Components",                "Exactly Once Delivery",              "Message Queues"),
    ("Components",                "Storage Systems",                    None),
    ("Components",                "Block vs File vs Object Storage",    "Storage Systems"),
    ("Components",                "API Gateway",                        None),
    ("Components",                "Rate Limiting",                      "API Gateway"),

    ("Distributed Systems",       "Consensus Algorithms",               None),
    ("Distributed Systems",       "Raft Consensus",                     "Consensus Algorithms"),
    ("Distributed Systems",       "Paxos",                              "Consensus Algorithms"),
    ("Distributed Systems",       "Leader Election",                    None),
    ("Distributed Systems",       "Distributed Transactions",           None),
    ("Distributed Systems",       "Two Phase Commit",                   "Distributed Transactions"),
    ("Distributed Systems",       "Saga Pattern",                       "Distributed Transactions"),
    ("Distributed Systems",       "Outbox Pattern",                     "Distributed Transactions"),
    ("Distributed Systems",       "Service Discovery",                  None),
    ("Distributed Systems",       "Distributed Locking",                None),
    ("Distributed Systems",       "Redlock Algorithm",                  "Distributed Locking"),
    ("Distributed Systems",       "Lamport Timestamps",                 None),
    ("Distributed Systems",       "Vector Clocks",                      None),
    ("Distributed Systems",       "Gossip Protocol",                    None),
    ("Distributed Systems",       "Quorum",                             None),
    ("Distributed Systems",       "Bloom Filters",                      None),

    ("Architectural Patterns",    "Monolith vs Microservices",          None),
    ("Architectural Patterns",    "Modular Monolith",                   "Monolith vs Microservices"),
    ("Architectural Patterns",    "Strangler Fig Pattern",              "Monolith vs Microservices"),
    ("Architectural Patterns",    "Microservices",                      None),
    ("Architectural Patterns",    "Service Mesh",                       "Microservices"),
    ("Architectural Patterns",    "Sidecar Pattern",                    "Microservices"),
    ("Architectural Patterns",    "Event Driven Architecture",          None),
    ("Architectural Patterns",    "Event Sourcing",                     "Event Driven Architecture"),
    ("Architectural Patterns",    "CQRS",                               "Event Driven Architecture"),
    ("Architectural Patterns",    "Serverless Architecture",            None),
    ("Architectural Patterns",    "Domain Driven Design",               None),
    ("Architectural Patterns",    "Bounded Contexts",                   "Domain Driven Design"),

    ("Data Systems",              "Data Warehouse vs Data Lake",        None),
    ("Data Systems",              "OLTP vs OLAP",                       None),
    ("Data Systems",              "ETL Pipelines",                      None),
    ("Data Systems",              "Stream Processing",                  None),
    ("Data Systems",              "Apache Flink",                       "Stream Processing"),
    ("Data Systems",              "Spark Streaming",                    "Stream Processing"),
    ("Data Systems",              "Batch Processing",                   None),
    ("Data Systems",              "Apache Spark",                       "Batch Processing"),
    ("Data Systems",              "Time Series Databases",              None),
    ("Data Systems",              "Column Oriented Databases",          None),

    ("Cloud and Infrastructure",  "Containers and Docker",              None),
    ("Cloud and Infrastructure",  "Kubernetes",                         None),
    ("Cloud and Infrastructure",  "Kubernetes Pods Services Deployments","Kubernetes"),
    ("Cloud and Infrastructure",  "Horizontal Pod Autoscaler",          "Kubernetes"),
    ("Cloud and Infrastructure",  "CI CD Pipelines",                    None),
    ("Cloud and Infrastructure",  "Infrastructure as Code",             None),
    ("Cloud and Infrastructure",  "Multi Region Architecture",          None),
    ("Cloud and Infrastructure",  "Active Active vs Active Passive",    "Multi Region Architecture"),

    ("Security",                  "Authentication",                     None),
    ("Security",                  "JWT",                                "Authentication"),
    ("Security",                  "OAuth 2.0",                          "Authentication"),
    ("Security",                  "OpenID Connect",                     "Authentication"),
    ("Security",                  "SSO and SAML",                       "Authentication"),
    ("Security",                  "Authorization",                      None),
    ("Security",                  "RBAC",                               "Authorization"),
    ("Security",                  "ABAC",                               "Authorization"),
    ("Security",                  "Data Security",                      None),
    ("Security",                  "Encryption at Rest and in Transit",  "Data Security"),
    ("Security",                  "Secrets Management",                 "Data Security"),
    ("Security",                  "DDoS Protection",                    None),
    ("Security",                  "OWASP Top 10",                       None),

    ("Observability",             "Metrics and Monitoring",             None),
    ("Observability",             "Prometheus and Grafana",             "Metrics and Monitoring"),
    ("Observability",             "Four Golden Signals",                "Metrics and Monitoring"),
    ("Observability",             "Logging",                            None),
    ("Observability",             "ELK Stack",                          "Logging"),
    ("Observability",             "Distributed Tracing",                None),
    ("Observability",             "OpenTelemetry",                      "Distributed Tracing"),
    ("Observability",             "SLI SLO SLA",                        None),

    ("Real-World Systems",        "URL Shortener",                      None),
    ("Real-World Systems",        "Rate Limiter",                       None),
    ("Real-World Systems",        "Chat System",                        None),
    ("Real-World Systems",        "Notification System",                None),
    ("Real-World Systems",        "Search Autocomplete",                None),
    ("Real-World Systems",        "News Feed System",                   None),
    ("Real-World Systems",        "Video Streaming Service",            None),
    ("Real-World Systems",        "Ride Sharing Service",               None),
    ("Real-World Systems",        "Web Crawler",                        None),
    ("Real-World Systems",        "Distributed Cache",                  None),
    ("Real-World Systems",        "Key Value Store",                    None),
    ("Real-World Systems",        "Unique ID Generator",                None),
    ("Real-World Systems",        "Google Maps",                        None),
    ("Real-World Systems",        "Payment System",                     None),
]

# ── Prompt ────────────────────────────────────────────────────────────────────

def make_prompt(topic: str, category: str, parent: str | None) -> str:
    context = f" (subtopic of {parent})" if parent else ""
    return f"""You are a system design expert writing a knowledge base.
Write a detailed explanation of "{topic}"{context} for the category "{category}".

Respond ONLY with a valid JSON object. No markdown fences, no explanation outside JSON.

Schema:
{{
  "keywords": ["5-10 relevant search keywords"],
  "content": "Detailed explanation, 200-400 words. Use **bold** for key terms. Cover: definition, how it works, key properties, tradeoffs, real-world usage. Include comparisons or examples where relevant.",
  "related": ["3-5 related system design topic names"]
}}"""


# ── Ollama call ───────────────────────────────────────────────────────────────

def call_ollama(prompt: str, model: str) -> str:
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 1024},
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    # Retry with exponential backoff for transient failures
    attempts = 3
    backoff = 1.0
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=60 + int((attempt-1)*30)) as resp:
                body = resp.read()
                try:
                    parsed = json.loads(body)
                    # common Ollama response shape: {"response": "..."}
                    if isinstance(parsed, dict) and "response" in parsed:
                        return str(parsed["response"]).strip()
                    # otherwise, return stringified body
                    return str(parsed).strip()
                except Exception:
                    return body.decode(errors="replace").strip()
        except KeyboardInterrupt:
            raise
        except Exception as e:
            if attempt == attempts:
                raise
            time.sleep(backoff)
            backoff *= 2

    # Should not reach here
    raise RuntimeError("Failed to call Ollama after retries")


def parse_response(raw: str) -> dict | None:
    # Strip markdown fences if model added them
    raw = raw.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'^```\s*',     '', raw)
    raw = re.sub(r'\s*```$',     '', raw)

    # Helper: extract first balanced JSON object
    def _extract_json_object(s: str) -> str | None:
        start = s.find('{')
        if start == -1:
            return None
        depth = 0
        for i in range(start, len(s)):
            ch = s[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return s[start:i+1]
        return None

    # Try direct parse first
    try:
        return json.loads(raw)
    except Exception:
        pass

    # If the model used backticks for multi-line strings (invalid JSON),
    # replace patterns like:  "content": `...`  with a proper JSON string.
    def _replace_backtick_values(s: str) -> str:
        def repl(m):
            inner = m.group(1)
            return ": " + json.dumps(inner)
        return re.sub(r':\s*`([^`]*)`', repl, s, flags=re.DOTALL)

    try:
        sanitized = _replace_backtick_values(raw)
        return json.loads(sanitized)
    except Exception:
        pass

    # Try extracting balanced JSON
    candidate = _extract_json_object(raw)
    if candidate:
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # Fallback: try non-greedy simple regex extraction
    match = re.search(r'\{.*?\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    return None


# ── Tree insertion ────────────────────────────────────────────────────────────

def insert(tree: dict, category: str, topic: str, parent: str | None, node: dict):
    root = tree.setdefault("System Design", {})
    cat  = root.setdefault(category, {})

    entry = {
        "keywords": node.get("keywords", []),
        "content":  node.get("content", ""),
        "related":  node.get("related", []),
    }

    if parent and parent in cat:
        # Insert as subtopic of parent
        cat[parent].setdefault("subtopics", {})[topic] = entry
    else:
        # Insert as top-level topic in category
        if topic not in cat:
            cat[topic] = entry
        else:
            # Already exists (from a previous run), just update
            cat[topic].update(entry)


# ── Progress ──────────────────────────────────────────────────────────────────

def load_progress() -> set:
    if Path(PROGRESS_FILE).exists():
        with open(PROGRESS_FILE) as f:
            return set(json.load(f))
    return set()


def save_progress(done: set):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(list(done), f)


# ── Main ──────────────────────────────────────────────────────────────────────

def run(model: str, merge: bool, dry_run: bool):
    # default: do not save raw debug responses unless explicitly requested
    # If CLI used --save-debug, a module-level flag '__save_debug_requested' is set.
    save_debug = bool(globals().get('__save_debug_requested', False))
    # Load existing KB if merging
    if merge and Path(OUTPUT_FILE).exists():
        with open(OUTPUT_FILE) as f:
            tree = json.load(f)
        print(f"✓ Loaded existing KB ({OUTPUT_FILE})")
    else:
        tree = {}

    done = load_progress()
    total = len(TOPICS)
    success = 0
    failed  = 0

    print(f"\n🚀 Generating {total} topics with Ollama ({model})\n")

    for i, (category, topic, parent) in enumerate(TOPICS):
        if topic in done:
            print(f"  [{i+1:3d}/{total}] ✓ Skip: {topic}")
            continue

        print(f"  [{i+1:3d}/{total}] Generating: {topic} ...", end=" ", flush=True)

        if dry_run:
            print("[DRY RUN]")
            continue

        prompt = make_prompt(topic, category, parent)

        try:
            raw  = call_ollama(prompt, model)
            node = parse_response(raw)

            if node:
                insert(tree, category, topic, parent, node)
                done.add(topic)
                save_progress(done)
                success += 1
                print("✓")
            else:
                failed += 1
                # Save raw response for debugging
                if save_debug:
                    dbg_dir = Path("data/raw")
                    dbg_dir.mkdir(parents=True, exist_ok=True)
                    safe_name = re.sub(r'[^A-Za-z0-9_.-]', '_', topic)[:80]
                    raw_path = dbg_dir / f"{safe_name}.raw.txt"
                    with open(raw_path, 'w', encoding='utf-8') as rf:
                        rf.write(raw or "")
                    print(f"✗ (bad JSON) — saved raw to: {raw_path}")
                else:
                    print("✗ (bad JSON)")

        except KeyboardInterrupt:
            print("\nInterrupted by user — saving progress and exiting.")
            # Save partial KB and progress
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(tree, f, indent=2, ensure_ascii=False)
            save_progress(done)
            raise
        except Exception as e:
            failed += 1
            print(f"✗ ({e})")

        time.sleep(DELAY_SECONDS)

    if not dry_run:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(tree, f, indent=2, ensure_ascii=False)

        # Count total topics
        topic_count = sum(
            len([k for k, v in cat.items() if isinstance(v, dict)])
            for cat in tree.get("System Design", {}).values()
        )

        print(f"\n{'='*50}")
        print(f"✅ Done!")
        print(f"   Success : {success}")
        print(f"   Failed  : {failed}")
        print(f"   KB topics: {topic_count}")
        print(f"   Saved to: {OUTPUT_FILE}")

        if failed:
            print(f"\n💡 Re-run to retry {failed} failed topics.")

        if Path(PROGRESS_FILE).exists() and failed == 0:
            Path(PROGRESS_FILE).unlink()
    else:
        print(f"\n[DRY RUN] Would generate {total} topics.")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate KB from topic list using local Ollama")
    parser.add_argument("--model",   default="llama3.1",  help="Ollama model name")
    parser.add_argument("--merge",   action="store_true", help="Merge into existing knowledge_base.json")
    parser.add_argument("--dry-run", action="store_true", help="Preview topics without calling Ollama")
    parser.add_argument("--save-debug", action="store_true", help="Save raw model responses on parse failures into debug_responses/")
    args = parser.parse_args()

    # Pass save-debug flag into runtime via environment-like variable
    # (set local variable before calling run)
    run_args = {
        'model': args.model,
        'merge': args.merge,
        'dry_run': args.dry_run,
    }

    # If user asked to save debug outputs, set flag in module scope
    if args.save_debug:
        # set variable used in run(); monkeypatch here for simplicity
        globals()['__save_debug_requested'] = True
    else:
        globals()['__save_debug_requested'] = False

    # Update run() to read the flag at start (backwards compatible)
    # Inserted: set save_debug variable from globals() inside run()
    # Call run
    run(**run_args)