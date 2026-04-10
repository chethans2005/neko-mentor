"""
navigator.py — Tree-based knowledge base navigator.

Core logic:
1. Start at root node
2. At each level, ask LLM which children are most relevant
3. Score children using: LLM score (70%) + keyword match (30%)
4. Use DFS with max depth = 5
5. Return best node with traversal path and confidence score
"""

import json
import os
from typing import Optional, Tuple
from llm import call_llm_async, parse_json_response
import asyncio


# ============================================================================
# NODE SCORING
# ============================================================================

def keyword_match_score(query_keywords: list, node: dict) -> float:
    """
    Score node based on keyword overlap with query.
    
    Args:
        query_keywords: Keywords extracted from query.
        node: A knowledge base node (dict).
    
    Returns:
        Score between 0 and 1.
    """
    if not query_keywords:
        return 0.0
    
    node_keywords = node.get("keywords", [])
    node_content = node.get("content", "").lower()
    
    matches = 0
    for kw in query_keywords:
        kw_lower = kw.lower()
        # Check in node keywords
        if any(kw_lower in nk.lower() for nk in node_keywords):
            matches += 1
        # Check in content (word boundary)
        elif f" {kw_lower} " in f" {node_content} ":
            matches += 0.5
    
    return min(1.0, matches / max(1, len(query_keywords)))


def name_match_score(query_keywords: list, node_name: str) -> float:
    """Score based on keyword overlap with node name."""
    if not query_keywords or not node_name:
        return 0.0
    node_name_lower = node_name.lower()
    matches = sum(1 for kw in query_keywords if kw.lower() in node_name_lower)
    return min(1.0, matches / max(1, len(query_keywords)))


def extract_children(node: dict) -> dict:
    """
    Extract children from a node.
    Children can be in 'children' or 'subtopics' key.
    
    Args:
        node: A knowledge base node.
    
    Returns:
        Dict of {name: node_dict}.
    """
    children = node.get("children", {})
    if children:
        return children

    children = node.get("subtopics", {})
    if children:
        return children

    # Fallback for KBs where nested topic groups are direct dict keys.
    # Exclude metadata/content keys that are not navigable children.
    ignored_keys = {"keywords", "content", "related", "summary", "examples"}
    inferred_children = {
        key: value
        for key, value in node.items()
        if key not in ignored_keys and isinstance(value, dict)
    }
    return inferred_children


def subtree_keyword_score(query_keywords: list, node: dict, max_depth: int = 2) -> float:
    """Best keyword score in a small subtree to support category-level nodes."""
    current = keyword_match_score(query_keywords, node)
    if max_depth <= 0:
        return current

    children = extract_children(node)
    if not children:
        return current

    best_descendant = current
    for child in children.values():
        child_score = subtree_keyword_score(query_keywords, child, max_depth=max_depth - 1)
        if child_score > best_descendant:
            best_descendant = child_score
    return best_descendant


# ============================================================================
# LLM-GUIDED SCORING
# ============================================================================

async def llm_score_children(
    query: str,
    current_node_name: str,
    children: dict,
    provider: str = "ollama",
    model: Optional[str] = None,
) -> dict:
    """
    Ask LLM to score children (top 2-3 most relevant).
    
    Args:
        query: User's query.
        current_node_name: Name of current node.
        children: Dict of {name: node_dict}.
        provider: "ollama" or "groq".
        model: Optional model name.
    
    Returns:
        Dict of {child_name: llm_score} where score is 0-1.
    """
    if not children:
        return {}
    
    # Limit to top 10 children for evaluation
    child_names = list(children.keys())[:10]
    child_list = "\n".join(f"- {name}" for name in child_names)
    
    prompt = f"""You are a system design expert. A user has this question:
"{query}"

We are currently at: {current_node_name}

Here are the child topics:
{child_list}

Rate each child's relevance to the user's query on a scale of 0-1.
Return ONLY a JSON object mapping child names to relevance scores.
Example: {{\\"Network Design\\": 0.9, \\"Caching\\": 0.3}}

Return valid JSON only, no markdown or explanation."""

    # Call async LLM interface
    response = await call_llm_async(prompt, provider=provider, model=model)
    scores = parse_json_response(response)
    
    # Validate: ensure all scores are between 0 and 1
    if not isinstance(scores, dict):
        scores = {}
    
    valid_scores = {}
    for name, score in scores.items():
        if isinstance(score, (int, float)):
            valid_scores[name] = max(0.0, min(1.0, float(score)))
        else:
            valid_scores[name] = 0.0
    
    return valid_scores


def combine_scores(
    llm_scores: dict,
    query_keywords: list,
    children: dict,
    llm_weight: float = 0.7,
    keyword_weight: float = 0.3,
) -> dict:
    """
    Combine LLM scores and keyword match scores.
    
    Args:
        llm_scores: Dict of {child_name: llm_score}.
        query_keywords: Keywords from query.
        children: Dict of {child_name: node_dict}.
        llm_weight: Weight for LLM scores (default 70%).
        keyword_weight: Weight for keyword scores (default 30%).
    
    Returns:
        Dict of {child_name: combined_score}.
    """
    combined = {}
    
    for child_name, child_node in children.items():
        llm_score = llm_scores.get(child_name, 0.0)
        kw_direct = keyword_match_score(query_keywords, child_node)
        kw_name = name_match_score(query_keywords, child_name)
        kw_subtree = subtree_keyword_score(query_keywords, child_node, max_depth=2)

        # Blend direct content match with name and descendant hints.
        kw_score = max(kw_direct, (0.5 * kw_name) + (0.5 * kw_subtree))
        
        combined_score = (llm_weight * llm_score) + (keyword_weight * kw_score)
        combined[child_name] = combined_score
    
    return combined


# ============================================================================
# TREE TRAVERSAL (DFS)
# ============================================================================

async def navigate_tree(
    query: str,
    query_keywords: list,
    root: dict,
    max_depth: int = 5,
    provider: str = "ollama",
    model: Optional[str] = None,
    debug: bool = False,
    deterministic: bool = False,
) -> dict:
    """
    Navigate the knowledge tree using DFS with LLM guidance.
    
    Args:
        query: User's query.
        query_keywords: Keywords extracted from query.
        root: Root node of knowledge tree.
        max_depth: Maximum depth to traverse (default 5).
        provider: "ollama" or "groq".
        model: Optional model name.
        debug: If True, log traversal path.
        deterministic: If True, skip LLM scoring and use keyword-only routing.
    
    Returns:
        Dict with:
            - best_node: The best node found (dict).
            - best_node_name: Name of best node (str).
            - path: List of node names from root to best node.
            - score: Final score (0-1).
            - depth: Depth at which best node was found.
    """
    best_node = root
    best_node_name = "System Design"
    best_score = 0.0
    path = ["System Design"]
    depth = 0
    
    current_node = root
    current_name = "System Design"
    
    for current_depth in range(max_depth):
        depth = current_depth
        
        # Get children
        children = extract_children(current_node)
        
        if not children:
            # Leaf node reached
            if debug:
                print(f"  Leaf node reached at depth {current_depth}: {current_name}")
            break
        
        # Score children
        if deterministic:
            llm_scores = {name: 0.0 for name in children.keys()}
            if debug:
                print("  Deterministic mode: using keyword-only scoring.")
        else:
            try:
                llm_scores = await llm_score_children(
                    query, current_name, children, provider=provider, model=model
                )
            except Exception as e:
                if debug:
                    print(f"  LLM scoring error: {e}. Using keyword-only scoring.")
                # No LLM: rely fully on heuristic scoring.
                llm_scores = {name: 0.0 for name in children.keys()}
        
        combined_scores = combine_scores(llm_scores, query_keywords, children)
        
        if not combined_scores:
            if debug:
                print(f"  No scored children at depth {current_depth}")
            break
        
        # Pick best child
        best_child_name = max(combined_scores, key=combined_scores.get)
        best_child_score = combined_scores[best_child_name]
        best_child_node = children[best_child_name]
        
        if debug:
            print(
                f"  Depth {current_depth}: {current_name} -> {best_child_name} "
                f"(score: {best_child_score:.2f})"
            )
        
        # Update traversal
        current_node = best_child_node
        current_name = best_child_name
        path.append(best_child_name)
        
        # Track best node
        if best_child_score > best_score:
            best_score = best_child_score
            best_node = best_child_node
            best_node_name = best_child_name
    
    return {
        "best_node": best_node,
        "best_node_name": best_node_name,
        "path": path,
        "score": best_score,
        "depth": depth,
    }


# ============================================================================
# CONFIDENCE AND FALLBACK
# ============================================================================

def compute_confidence(score: float, depth: int) -> float:
    """
    Compute confidence score.
    
    confidence = min(1.0, score + depth * 0.05)
    
    Args:
        score: Base score (0-1).
        depth: Depth at which node was found.
    
    Returns:
        Confidence score (0-1).
    """
    return min(1.0, score + (depth * 0.05))


def full_tree_traversal(
    query: str,
    query_keywords: list,
    node: dict,
    node_name: str = "",
    best_result: Optional[Tuple] = None,
) -> Tuple[dict, str, list, float]:
    """
    Perform exhaustive keyword-based tree traversal (fallback).
    
    Args:
        query: User's query.
        query_keywords: Keywords from query.
        node: Current node.
        node_name: Name of current node.
        best_result: Running best (node, name, path, score).
    
    Returns:
        Tuple of (best_node, best_node_name, path, best_score).
    """
    if best_result is None:
        best_result = (node, node_name, [node_name], 0.0)
    
    best_node, best_name, best_path, best_score = best_result
    
    # Score current node
    current_score = keyword_match_score(query_keywords, node)
    
    if current_score > best_score:
        best_score = current_score
        best_node = node
        best_name = node_name
        best_path = best_path[:-1] + [node_name]
    
    # Recurse to children
    children = extract_children(node)
    for child_name, child_node in children.items():
        new_path = best_path + [child_name]
        bn, bname, bpath, bscore = full_tree_traversal(
            query,
            query_keywords,
            child_node,
            child_name,
            (best_node, best_name, new_path, best_score),
        )
        
        if bscore > best_score:
            best_score = bscore
            best_node = bn
            best_name = bname
            best_path = bpath
    
    return best_node, best_name, best_path, best_score


if __name__ == "__main__":
    # Simple test
    import sys
    sys.path.append("data/kb")
    
    async def _run():
        try:
            kb_path = "shared/data/kb/knowledge_base.json"
            if not os.path.exists(kb_path):
                kb_path = "data/kb/knowledge_base.json"

            with open(kb_path, "r") as f:
                kb_full = json.load(f)

            root = kb_full.get("System Design", {})

            query = "How does consistent hashing work?"
            query_keywords = ["consistent", "hashing", "distributed"]

            print(f"Query: {query}")
            print(f"Keywords: {query_keywords}\n")

            result = await navigate_tree(query, query_keywords, root, debug=True)
            print(f"\nBest node: {result['best_node_name']}")
            print(f"Path: {' -> '.join(result['path'])}")
            print(f"Score: {result['score']:.2f}")
            print(f"Confidence: {compute_confidence(result['score'], result['depth']):.2f}")

        except FileNotFoundError:
            print("KB file not found. Run from project root.")

    asyncio.run(_run())
