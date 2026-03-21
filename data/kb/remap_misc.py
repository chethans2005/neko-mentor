"""Remap 'Misc' topics into proper categories using `generate_kb.TOPICS`.

Usage:
    python remap_misc.py
"""
from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parent
KB_PATH = ROOT / 'knowledge_base.json'

def load_kb():
    return json.loads(KB_PATH.read_text(encoding='utf-8'))

def save_kb(kb):
    KB_PATH.write_text(json.dumps(kb, indent=2, ensure_ascii=False), encoding='utf-8')

def normalize(s: str) -> str:
    return ''.join(c.lower() if c.isalnum() else ' ' for c in s).strip()

def main():
    sys.path.insert(0, str(ROOT))
    try:
        import generate_kb as gen
        topics_map = {normalize(t[1]): (t[0], t[2], t[1]) for t in gen.TOPICS}
    finally:
        sys.path.pop(0)

    kb = load_kb()
    root = kb.setdefault('System Design', {})
    misc = root.get('Misc')
    if not misc:
        print('No Misc category found; nothing to do')
        return

    moved = 0
    renamed = 0
    for key in list(misc.keys()):
        entry = misc.pop(key)
        # Clean key name
        clean = key
        if clean.endswith('.raw') or clean.endswith('.raw.txt'):
            clean = clean.replace('.raw.txt','').replace('.raw','')
        clean = clean.strip()

        lookup = normalize(clean)
        found = topics_map.get(lookup)
        if found:
            category, parent, canonical = found
            cat = root.setdefault(category, {})
            # If parent exists and present in category, insert as subtopic
            if parent and parent in cat:
                cat[parent].setdefault('subtopics', {})[canonical] = entry
            else:
                cat[canonical] = entry
            moved += 1
            print(f"Moved: {clean} -> {category} / {canonical} (parent={parent})")
        else:
            # Rename key removing .raw etc and keep in Misc
            if clean != key:
                misc[clean] = entry
                renamed += 1
                print(f"Renamed in Misc: {key} -> {clean}")
            else:
                misc[key] = entry

    # If Misc empty now, remove it
    if not misc:
        root.pop('Misc', None)

    save_kb(kb)
    print(f"Done. Moved: {moved}, Renamed in Misc: {renamed}")

if __name__ == '__main__':
    main()
