"""
build_kb_local.py — Same pipeline but reads from LOCAL markdown files.

Use this if you've already cloned the repos or have your own markdown files.

Usage:
    # Clone sources first:
    git clone https://github.com/donnemartin/system-design-primer
    git clone https://github.com/karanpratapsingh/system-design
    git clone https://github.com/ByteByteGoHq/system-design-101

    # Then run:
    export GROQ_API_KEY="your_key"
    python build_kb_local.py --dirs ./system-design-primer ./system-design ./system-design-101
    python build_kb_local.py --dirs ./my-notes --merge   # merge into existing KB
"""

import os
import re
import json
import time
import argparse
from pathlib import Path
from groq import Groq

GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL    = "llama3-8b-8192"
# Use centralized data folders
OUTPUT_FILE   = os.path.join("data", "kb", "knowledge_base.json")
PROGRESS_FILE = os.path.join("data", "progress", "build_progress_local.json")
RATE_LIMIT_DELAY = 2.2
CHUNK_MIN_WORDS  = 80
CHUNK_MAX_WORDS  = 600

# Map folder name keywords to KB categories
FOLDER_CATEGORY_MAP = {
    "primer":        "Fundamentals",
    "karanpratap":   "Components",
    "bytebytego":    "Real-World Systems",
    "101":           "Real-World Systems",
    "distributed":   "Distributed Systems",
    "cloud":         "Cloud & Infrastructure",
    "security":      "Security",
    "database":      "Components",
    "networking":    "Networking",
}

SYSTEM_PROMPT = """You are a system design knowledge base builder.
Convert the given markdown content into a structured JSON node.
Respond ONLY with valid JSON. No markdown fences, no explanation, no preamble.

Required schema:
{
  "topic_name": "Short clear name for this topic (3-5 words max)",
  "category": "One of: Fundamentals | Components | Distributed Systems | Architectural Patterns | Real-World Systems | Security | Observability | Networking | Data Systems | Cloud & Infrastructure",
  "keywords": ["5-10 relevant search keywords"],
  "content": "Well-written explanation (200-500 words). Use **bold** for key terms. Include: definition, how it works, key properties, tradeoffs, real-world usage.",
  "related": ["2-5 related topic names"],
  "subtopics": {}
}

Rules:
- subtopics only if content naturally breaks into 2+ distinct sub-concepts
- Never include source URLs, author names, or GitHub references
- content must be factually accurate system design knowledge
"""


def guess_category(filepath: Path) -> str:
    """Guess KB category from file path."""
    path_str = str(filepath).lower()
    for keyword, category in FOLDER_CATEGORY_MAP.items():
        if keyword in path_str:
            return category
    return "Fundamentals"


def find_markdown_files(dirs: list[str]) -> list[Path]:
    """Recursively find all .md files in given directories."""
    files = []
    for d in dirs:
        p = Path(d)
        if p.is_file() and p.suffix == ".md":
            files.append(p)
        elif p.is_dir():
            files.extend(p.rglob("*.md"))
    # Exclude common noise files
    files = [f for f in files if f.name.lower() not in {
        "license.md", "contributing.md", "changelog.md", "code_of_conduct.md"
    }]
    return sorted(files)


def chunk_file(filepath: Path, category: str) -> list[dict]:
    """Split a markdown file into chunks at ## headings."""
    try:
        text = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"  ⚠ Could not read {filepath}: {e}")
        return []

    pattern = r'(?=^#{1,3} .+$)'
    sections = re.split(pattern, text, flags=re.MULTILINE)

    chunks = []
    for section in sections:
        lines = section.strip().splitlines()
        if not lines:
            continue

        heading_line = lines[0].strip()
        if not heading_line.startswith("#"):
            continue

        heading = re.sub(r'^#{1,6}\s+', '', heading_line).strip()
        body = "\n".join(lines[1:]).strip()

        if len(body.split()) < CHUNK_MIN_WORDS:
            continue
        if body.count("](") > 10:  # TOC-like
            continue

        words = body.split()
        if len(words) > CHUNK_MAX_WORDS:
            body = " ".join(words[:CHUNK_MAX_WORDS]) + "\n\n[...trimmed]"

        chunks.append({
            "heading": heading,
            "content": f"# {heading}\n\n{body}",
            "category": category,
            "source_file": str(filepath),
        })

    return chunks


def chunk_to_kb_node(client: Groq, chunk: dict) -> dict | None:
    prompt = f"""Convert this system design content into the required JSON schema.
Topic hint: "{chunk['heading']}"
Suggested category: "{chunk['category']}"

Content:
{chunk['content']}
"""
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1200,
        )
        # Defensive access and JSON extraction
        raw = None
        try:
            raw = response.choices[0].message.content.strip()
        except Exception:
            try:
                raw = response['choices'][0]['message']['content'].strip()
            except Exception:
                raw = str(response)

        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'^```\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

        # Try extracting a JSON object if enclosed
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

        candidate = _extract_json_object(raw) or raw
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            print(f"    ✗ JSON parse error for '{chunk['heading']}'")
            return None
    except json.JSONDecodeError as e:
        print(f"    ✗ JSON parse error for '{chunk['heading']}': {e}")
        return None
    except Exception as e:
        print(f"    ✗ API error for '{chunk['heading']}': {e}")
        return None


def insert_node(tree: dict, node: dict) -> dict:
    category = node.get("category", "Fundamentals").strip()
    topic    = node.get("topic_name", "Unknown").strip()

    root = tree.setdefault("System Design", {})
    cat  = root.setdefault(category, {})

    if topic in cat:
        existing = cat[topic]
        existing.setdefault("keywords", [])
        existing.setdefault("related", [])

        new_keywords = set(existing.get("keywords", [])) | set(node.get("keywords", []))
        existing["keywords"] = sorted([k for k in new_keywords if k])

        new_related = set(existing.get("related", [])) | set(node.get("related", []))
        existing["related"] = sorted([r for r in new_related if r])

        new_content = node.get("content", "")
        if len(new_content or "") > len(existing.get("content", "")):
            existing["content"] = new_content

        new_subs = node.get("subtopics", {})
        if new_subs:
            existing.setdefault("subtopics", {}).update(new_subs)

        print(f"    ~ Merged: {category} > {topic}")
    else:
        cat[topic] = {
            "keywords": node.get("keywords", []),
            "content":  node.get("content", ""),
            "related":  node.get("related", []),
        }
        if node.get("subtopics"):
            cat[topic]["subtopics"] = node["subtopics"]
        print(f"    ✓ Added: {category} > {topic}")

    return tree


def load_progress() -> set:
    if Path(PROGRESS_FILE).exists():
        with open(PROGRESS_FILE) as f:
            return set(json.load(f))
    return set()


def save_progress(done: set):
    Path(PROGRESS_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(done), f)


def run(dirs: list[str], dry_run: bool = False, merge: bool = False):
    if not dry_run and not GROQ_API_KEY:
        print("❌ Set GROQ_API_KEY environment variable first.")
        print("   Get a free key at: https://console.groq.com")
        return

    # Load existing KB
    if merge and Path(OUTPUT_FILE).exists():
        with open(OUTPUT_FILE) as f:
            tree = json.load(f)
        print(f"✓ Loaded existing KB from {OUTPUT_FILE}")
    else:
        tree = {}

    # Find all markdown files
    md_files = find_markdown_files(dirs)
    print(f"\n📂 Found {len(md_files)} markdown files across {len(dirs)} directories")

    client = Groq(api_key=GROQ_API_KEY) if not dry_run else None
    done = load_progress()

    total_chunks = 0
    success = 0
    failed  = 0

    for filepath in md_files:
        category = guess_category(filepath)
        chunks = chunk_file(filepath, category)

        if not chunks:
            continue

        print(f"\n📄 {filepath.name} ({len(chunks)} chunks) [{category}]")
        total_chunks += len(chunks)

        for i, chunk in enumerate(chunks):
            heading = f"{filepath.name}::{chunk['heading']}"

            if heading in done:
                print(f"  [{i+1}/{len(chunks)}] Skip (done): {chunk['heading']}")
                continue

            print(f"  [{i+1}/{len(chunks)}] {chunk['heading']}")

            if dry_run:
                print(f"    [DRY RUN] {len(chunk['content'].split())} words")
                continue

            node = chunk_to_kb_node(client, chunk)

            if node:
                tree = insert_node(tree, node)
                done.add(heading)
                save_progress(done)
                success += 1
            else:
                failed += 1

            time.sleep(RATE_LIMIT_DELAY)

    if not dry_run:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(tree, f, indent=2, ensure_ascii=False)

        topic_count = sum(
            len([k for k, v in cat.items() if isinstance(v, dict)])
            for cat in tree.get("System Design", {}).values()
        )

        print(f"\n{'='*60}")
        print(f"✅ Done!")
        print(f"   Chunks processed: {success}/{total_chunks}")
        print(f"   Failed chunks:    {failed}")
        print(f"   Total KB topics:  {topic_count}")
        print(f"   Saved to:         {OUTPUT_FILE}")

        if failed > 0:
            print(f"\n💡 Tip: Re-run with --merge to retry failed chunks.")

        if Path(PROGRESS_FILE).exists():
            Path(PROGRESS_FILE).unlink()
    else:
        print(f"\n[DRY RUN] Would process {total_chunks} chunks from {len(md_files)} files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build KB from local markdown files using Groq")
    parser.add_argument("--dirs",    nargs="+", required=True, help="Directories or .md files to process")
    parser.add_argument("--dry-run", action="store_true",      help="Preview without calling API")
    parser.add_argument("--merge",   action="store_true",      help="Merge into existing knowledge_base.json")
    parser.add_argument("--model",   default="llama3-8b-8192", help="Groq model to use")
    args = parser.parse_args()

    GROQ_MODEL = args.model
    run(args.dirs, dry_run=args.dry_run, merge=args.merge)