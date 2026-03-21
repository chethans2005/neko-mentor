"""
kb_stats.py — Inspect and validate knowledge_base.json

Usage:
    python kb_stats.py --file data/kb/knowledge_base.json --validate
"""
import json
import argparse
from pathlib import Path


def load_kb(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"KB file not found: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


def validate(kb: dict) -> dict:
    problems = {
        'missing_root': False,
        'empty_categories': [],
        'topics_missing_keywords': [],
        'topics_missing_content': [],
        'total_categories': 0,
        'total_topics': 0,
    }

    if 'System Design' not in kb:
        problems['missing_root'] = True
        return problems

    root = kb['System Design']
    problems['total_categories'] = len(root)

    for cat, topics in root.items():
        if not isinstance(topics, dict) or len(topics) == 0:
            problems['empty_categories'].append(cat)
            continue

        for tname, entry in topics.items():
            if not isinstance(entry, dict):
                continue
            problems['total_topics'] += 1
            kws = entry.get('keywords', [])
            content = entry.get('content', '')
            if not kws:
                problems['topics_missing_keywords'].append(f"{cat} > {tname}")
            if not (isinstance(content, str) and content.strip() and len(content.strip()) > 20):
                problems['topics_missing_content'].append(f"{cat} > {tname}")

    return problems


def show_report(problems: dict, path: str):
    print(f"KB file: {path}")
    if problems.get('missing_root'):
        print("✗ Missing top-level 'System Design' root")
        return

    print(f"Categories: {problems['total_categories']}")
    print(f"Topics: {problems['total_topics']}")

    if problems['empty_categories']:
        print(f"⚠ Empty categories: {len(problems['empty_categories'])} -> {problems['empty_categories'][:10]}")

    if problems['topics_missing_keywords']:
        print(f"⚠ Topics missing keywords: {len(problems['topics_missing_keywords'])}")
        for t in problems['topics_missing_keywords'][:20]:
            print(f"  - {t}")

    if problems['topics_missing_content']:
        print(f"⚠ Topics missing content (too short or empty): {len(problems['topics_missing_content'])}")
        for t in problems['topics_missing_content'][:20]:
            print(f"  - {t}")

    if not problems['topics_missing_content'] and not problems['topics_missing_keywords'] and not problems['empty_categories']:
        print("✓ Looks good: KB appears populated and valid (basic checks)")


def main():
    parser = argparse.ArgumentParser(description='Inspect and validate knowledge base JSON')
    parser.add_argument('--file', default='data/kb/knowledge_base.json', help='Path to knowledge_base.json')
    parser.add_argument('--validate', action='store_true', help='Run validation checks')
    args = parser.parse_args()

    kb = load_kb(args.file)
    if args.validate:
        problems = validate(kb)
        show_report(problems, args.file)
    else:
        # Quick summary
        cats = list(kb.get('System Design', {}).keys())
        total_topics = sum(len(v) for v in kb.get('System Design', {}).values())
        print(f"KB: {args.file} — categories: {len(cats)}, topics (raw dict entries): {total_topics}")


if __name__ == '__main__':
    main()
