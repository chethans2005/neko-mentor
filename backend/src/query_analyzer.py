"""
query_analyzer.py — Query analysis using LLM.

Extracts intent, keywords, and domain from user queries.
"""

import json
import re
from typing import Optional
from llm import call_llm, parse_json_response


# ============================================================================
# QUERY ANALYZER
# ============================================================================

def analyze_query(
    query: str,
    provider: str = "ollama",
    model: Optional[str] = None,
) -> dict:
    """
    Analyze a user query to extract intent, keywords, and domain.
    
    Args:
        query: The user's question/query.
        provider: "ollama" or "groq".
        model: Optional model name. Uses default if not provided.
    
    Returns:
        Dict with keys:
            - intent: str (e.g., "understand", "compare", "troubleshoot")
            - keywords: list of str
            - domain: str (e.g., "databases", "networking", "security")
    """
    prompt = f"""Analyze this system design question and return JSON only.

Question: "{query}"

Return a JSON object with these fields:
- intent: One of ["understand", "compare", "troubleshoot", "design", "explain"]
- keywords: List of 3-5 technical keywords extracted from the question
- domain: One of ["databases", "networking", "security", "caching", "messaging", "scalability", "distributed-systems", "general"]

Return ONLY valid JSON, no markdown, no explanation."""

    try:
        response = call_llm(prompt, provider=provider, model=model)
        result = parse_json_response(response)
    except Exception:
        # Graceful fallback when provider is unavailable.
        result = {}
    
    # Validate and provide defaults
    if not isinstance(result, dict):
        result = {}
    
    result.setdefault("intent", "understand")
    result.setdefault("keywords", [])
    result.setdefault("domain", "general")
    
    # Ensure keywords is a list of strings
    if not isinstance(result.get("keywords"), list):
        result["keywords"] = []
    normalized_keywords = []
    for keyword in result["keywords"]:
        text = str(keyword).strip()
        if not text:
            continue
        # Split multi-word phrases so matching works with single-term KB keywords.
        parts = re.findall(r"[A-Za-z0-9-]+", text.lower())
        if parts:
            normalized_keywords.extend(parts)
    result["keywords"] = normalized_keywords

    # If LLM returns empty/invalid keywords, use heuristic extraction.
    if not result["keywords"]:
        result["keywords"] = extract_keywords_from_text(query)[:5]
    
    return result


def extract_keywords_from_text(text: str) -> list:
    """
    Simple keyword extraction from text (heuristic fallback).
    Splits on spaces and filters short words.
    
    Args:
        text: The text to extract keywords from.
    
    Returns:
        List of keywords.
    """
    raw_words = re.findall(r"[A-Za-z0-9-]+", text)
    words = [(raw, raw.lower()) for raw in raw_words]
    # Keep useful technical tokens and acronyms while removing stop words.
    common = {
        "the", "a", "an", "and", "or", "in", "at", "to", "for",
        "how", "what", "is", "are", "does", "do", "work", "works",
    }
    filtered = [
        lower for raw, lower in words
        if lower not in common and ((len(lower) >= 4) or raw.isupper() or lower.isdigit())
    ]
    return filtered


if __name__ == "__main__":
    # Test the analyzer
    test_queries = [
        "How do I implement consistent hashing?",
        "What's the difference between FIFO and LIFO queues?",
        "How does database sharding work?",
    ]
    
    for q in test_queries:
        print(f"\nQuery: {q}")
        try:
            analysis = analyze_query(q, provider="ollama")
            print(f"Analysis: {json.dumps(analysis, indent=2)}")
        except Exception as e:
            print(f"Error: {e}")
