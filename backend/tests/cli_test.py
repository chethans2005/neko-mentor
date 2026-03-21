"""
cli_test.py — Command-line testing without running the FastAPI server.

Usage:
    python cli_test.py "What is consistent hashing?"
    python cli_test.py "How does load balancing work?" --debug
    python cli_test.py "What is CAP theorem?" --provider groq --model mixtral-8x7b-32768
    python cli_test.py "Test query" --no-answer (just navigate, don't generate answer)
"""

import json
import sys
import os
import argparse

# Add backend/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from query_analyzer import analyze_query
from navigator import navigate_tree, compute_confidence
from answer_generator import generate_answer, extract_excerpt


# ============================================================================
# MAIN TEST FUNCTION
# ============================================================================

def test_query(
    query: str,
    debug: bool = False,
    provider: str = "ollama",
    model: str = None,
    no_answer: bool = False,
    deterministic: bool = False,
):
    """
    Test a query against the knowledge base.
    
    Args:
        query: User query.
        debug: Show debug info.
        provider: "ollama" or "groq".
        model: Optional model name.
        no_answer: Skip answer generation.
        deterministic: Use keyword-only routing (no LLM scoring in traversal).
    """
    
    # Load KB
    kb_path = "shared/data/kb/knowledge_base.json"
    if not os.path.exists(kb_path):
        kb_path = "data/kb/knowledge_base.json"

    if not os.path.exists(kb_path):
        print(f"✗ KB not found at {kb_path}")
        return
    
    with open(kb_path, "r") as f:
        kb_full = json.load(f)
    
    root = kb_full.get("System Design", {})
    if not root:
        print("✗ KB root not found")
        return
    
    print(f"\n{'='*70}")
    print(f"Query: {query}")
    print(f"Provider: {provider}")
    print(f"Deterministic: {deterministic}")
    if model:
        print(f"Model: {model}")
    print(f"{'='*70}\n")
    
    # Analyze query
    print("[1/3] Analyzing query...")
    try:
        analysis = analyze_query(query, provider=provider, model=model)
        keywords = analysis.get("keywords", [])
        intent = analysis.get("intent", "unknown")
        domain = analysis.get("domain", "general")
        
        print(f"  Intent: {intent}")
        print(f"  Domain: {domain}")
        print(f"  Keywords: {', '.join(keywords)}\n")
    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        keywords = []
    
    # Navigate tree
    print("[2/3] Navigating knowledge tree...")
    try:
        nav_result = navigate_tree(
            query,
            keywords,
            root,
            provider=provider,
            model=model,
            debug=debug,
            deterministic=deterministic,
        )
        
        best_node = nav_result["best_node"]
        best_node_name = nav_result["best_node_name"]
        path = nav_result["path"]
        score = nav_result["score"]
        depth = nav_result["depth"]
        
        print(f"  Best node: {best_node_name}")
        print(f"  Path: {' > '.join(path)}")
        print(f"  Depth: {depth}, Score: {score:.2f}")
        print(f"  Confidence: {compute_confidence(score, depth):.2f}\n")
    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        return
    
    # Generate answer
    if not no_answer:
        print("[3/3] Generating answer...")
        node_content = best_node.get("content", "")
        
        try:
            answer = generate_answer(
                query,
                node_content,
                path,
                provider=provider,
                model=model,
            )
            print(f"\n{answer}\n")
        except Exception as e:
            print(f"  ✗ Answer generation error: {e}")
            print(f"\n  Fallback excerpt:\n")
            excerpt = extract_excerpt(node_content, 400)
            print(f"  {excerpt}\n")
    else:
        print("[3/3] Skipped answer generation\n")


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Parse arguments and run test."""
    parser = argparse.ArgumentParser(
        description="CLI test for Vectorless System Design Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli_test.py "What is consistent hashing?"
  python cli_test.py "How does load balancing work?" --debug
  python cli_test.py "What is CAP theorem?" --provider groq --model mixtral-8x7b-32768
  python cli_test.py "Test query" --no-answer
        """,
    )
    
    parser.add_argument("query", help="Query to test")
    parser.add_argument(
        "--debug", action="store_true", help="Show debug information"
    )
    parser.add_argument(
        "--provider", default="ollama", choices=["ollama", "groq"],
        help="LLM provider (default: ollama)"
    )
    parser.add_argument(
        "--model", default=None, help="Model name (uses default if not specified)"
    )
    parser.add_argument(
        "--no-answer", action="store_true", help="Skip answer generation"
    )
    parser.add_argument(
        "--deterministic",
        action="store_true",
        help="Use keyword-only navigation (no LLM scoring)",
    )
    
    args = parser.parse_args()
    
    try:
        test_query(
            args.query,
            debug=args.debug,
            provider=args.provider,
            model=args.model,
            no_answer=args.no_answer,
            deterministic=args.deterministic,
        )
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
