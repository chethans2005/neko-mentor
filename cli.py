"""
cli.py — Test the navigator from the command line without starting a server.

Usage:
    python cli.py "How does consistent hashing work?"
    python cli.py "What is the difference between Kafka and RabbitMQ?"
"""

import sys
import json
from pathlib import Path


def load_knowledge_base(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"KB file not found: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


def navigate(query: str, kb: dict) -> dict:
    # Simple fallback navigator: score topics by keyword/title/content matches
    q = query.lower()
    best = None
    best_score = 0
    best_path = []
    best_answer = ""

    root = kb.get('System Design', {}) if isinstance(kb, dict) else {}
    for cat, topics in root.items():
        if not isinstance(topics, dict):
            continue
        for tname, entry in topics.items():
            score = 0
            title = tname.lower()
            content = (entry.get('content') or '')
            kws = entry.get('keywords') or []

            if q in title:
                score += 50
            if any(q in kw.lower() for kw in kws if isinstance(kw, str)):
                score += 30
            # count occurrences in content
            score += content.lower().count(q)

            # small boost for longer content
            if isinstance(content, str) and len(content) > 500:
                score += 5

            if score > best_score:
                best_score = score
                best = entry
                best_path = [cat, tname]
                best_answer = content

    confidence = min(1.0, best_score / 100) if best_score else 0.0
    return {
        'path': best_path or ['Unknown'],
        'confidence': round(confidence, 2),
        'answer': best_answer or 'No matching content found.'
    }


def main():
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Query: ")

    if not query.strip():
        print("Please provide a query.")
        return

    print(f"\n🔍 Query: {query}")
    print("─" * 60)

    # Default KB path (updated to the project's data layout)
    kb_path = Path('data') / 'kb' / 'knowledge_base.json'
    try:
        kb = load_knowledge_base(str(kb_path))
    except FileNotFoundError:
        print(f"KB not found at {kb_path}. Try running the build/generate scripts first.")
        return

    result = navigate(query, kb)

    print(f"📍 Path:       {' > '.join(result['path'])}")
    print(f"🎯 Confidence: {result['confidence']}")
    print(f"\n📖 Answer:\n{result['answer'][:1000]}{'...' if len(result['answer']) > 1000 else ''}")
    print("\n" + "─" * 60)


if __name__ == "__main__":
    main()
