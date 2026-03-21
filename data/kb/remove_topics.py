"""Remove specified topics from knowledge_base.json so the generator will recreate them."""
import json
from pathlib import Path

KB = Path(__file__).resolve().parent / 'knowledge_base.json'
TO_REMOVE = [
    ('Components', 'Load Balancing'),
    ('Data Systems', 'Time Series Databases'),
    ('Architectural Patterns', 'Monolith vs Microservices'),
]

def main():
    kb = json.loads(KB.read_text(encoding='utf-8'))
    root = kb.get('System Design', {})
    for cat, topic in TO_REMOVE:
        cat_map = root.get(cat)
        if cat_map and topic in cat_map:
            print(f"Removing: {cat} > {topic}")
            cat_map.pop(topic, None)
            # if category is empty, remove it
            if not cat_map:
                root.pop(cat, None)
    KB.write_text(json.dumps(kb, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Done')

if __name__ == '__main__':
    main()
