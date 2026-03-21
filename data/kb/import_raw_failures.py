"""Import raw Ollama responses (data/raw/*.raw.txt) into the KB.

Usage:
    python import_raw_failures.py
"""
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = ROOT / 'data' / 'raw'
KB_PATH = ROOT / 'data' / 'kb' / 'knowledge_base.json'


def load_topics():
    # import the TOPICS mapping from data/kb/generate_kb.py
    sys.path.insert(0, str(ROOT / 'data' / 'kb'))
    try:
        import generate_kb as gen
        topics_map = {t[1].lower(): (t[0], t[2]) for t in gen.TOPICS}
        return topics_map, gen
    finally:
        sys.path.pop(0)


def load_kb():
    if KB_PATH.exists():
        return json.loads(KB_PATH.read_text(encoding='utf-8'))
    return {}


def save_kb(kb: dict):
    KB_PATH.parent.mkdir(parents=True, exist_ok=True)
    KB_PATH.write_text(json.dumps(kb, indent=2, ensure_ascii=False), encoding='utf-8')


def insert(kb: dict, category: str, topic: str, parent: str | None, node: dict):
    root = kb.setdefault('System Design', {})
    cat = root.setdefault(category, {})
    entry = {
        'keywords': node.get('keywords', []),
        'content': node.get('content', ''),
        'related': node.get('related', []),
    }
    if parent and parent in cat:
        cat[parent].setdefault('subtopics', {})[topic] = entry
    else:
        cat.setdefault(topic, {}).update(entry)


def normalize_name(stem: str) -> str:
    # Turn file stem like 'Redis_vs_Memcached' -> 'Redis vs Memcached'
    name = stem.replace('_', ' ').replace('  ', ' ').strip()
    return name


def main():
    topics_map, gen = load_topics()
    kb = load_kb()
    files = sorted(RAW_DIR.glob('*.raw.txt')) if RAW_DIR.exists() else []
    if not files:
        print('No raw files found in', RAW_DIR)
        return

    added = 0
    failed = []

    for f in files:
        stem = f.stem
        topic_guess = normalize_name(stem)
        key = topic_guess.lower()
        category, parent = topics_map.get(key, ('Misc', None))

        raw = f.read_text(encoding='utf-8')

        # Use generate_kb.parse_response() which already implements
        # robust sanitization (backtick handling, balanced-extract, etc.)
        # First try the robust parser from generate_kb
        try:
            node = gen.parse_response(raw)
        except Exception as e:
            node = None

        # If that failed, attempt a targeted repair: replace the raw "content" block
        # (which may contain unescaped newlines) with a properly JSON-escaped string.
        if not node:
            try:
                import json as _json
                low = raw.lower()
                if '"content"' in low and '"related"' in low:
                    # find the positions in the original (case-sensitive) string
                    cpos = raw.find('"content"')
                    rpos = raw.find('"related"', cpos)
                    if cpos != -1 and rpos != -1 and rpos > cpos:
                        # locate the colon after content key
                        colon = raw.find(':', cpos)
                        content_text = raw[colon+1:rpos]
                        # strip surrounding commas/quotes/fences
                        content_text = content_text.strip().lstrip('"').rstrip(',').rstrip()
                        # remove triple backtick fences if present
                        content_text = content_text.replace('```json', '').replace('```', '')
                        content_text = content_text.strip()
                        new_raw = raw[:colon+1] + ' ' + _json.dumps(content_text) + '\n' + raw[rpos:]
                        node = gen.parse_response(new_raw)
                else:
                    node = None
            except Exception as e:
                node = None

        if not node:
            # Last-resort: attempt manual extraction of keywords, content, related
            try:
                import re
                kc = []
                rel = []

                m_kw = re.search(r'"keywords"\s*:\s*\[(.*?)\]', raw, re.DOTALL)
                if m_kw:
                    items = m_kw.group(1)
                    kws = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', items)
                    kc = [k.strip() for k in kws if k.strip()]

                m_rel = re.search(r'"related"\s*:\s*\[(.*?)\]', raw, re.DOTALL)
                if m_rel:
                    items = m_rel.group(1)
                    rls = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', items)
                    rel = [r.strip() for r in rls if r.strip()]

                # content: take text between "content" and "related" (or closing brace)
                content_text = ''
                m_cont = re.search(r'"content"\s*:\s*(.*?)(?:,\s*"related"|\}\s*$)', raw, re.DOTALL)
                if m_cont:
                    block = m_cont.group(1)
                    # strip surrounding quotes/backticks and trailing commas
                    block = block.strip()
                    if block.startswith('"') and block.endswith('"'):
                        block = block[1:-1]
                    block = block.replace('```json', '').replace('```', '').strip()
                    content_text = block

                # If we have at least content or keywords, construct node
                if content_text or kc or rel:
                    node = {'keywords': kc, 'content': content_text, 'related': rel}
                else:
                    node = None
            except Exception:
                node = None

            if not node:
                failed.append((f.name, 'could not extract fields'))
                continue

        insert(kb, category, topic_guess, parent, node)
        print(f"Imported: {topic_guess} -> {category} (parent={parent})")
        added += 1

    save_kb(kb)
    print('Done. Imported:', added)
    if failed:
        print('Failed to import:', len(failed))
        for name, err in failed:
            print(' -', name, err)


if __name__ == '__main__':
    main()
