"""
answer_generator.py — Generate answers using LLM based on selected node.

Takes the best-matched node content and the original query,
then asks an LLM to generate a comprehensive answer.
"""

from typing import Optional
from llm import call_llm


# ============================================================================
# ANSWER GENERATION
# ============================================================================

def generate_answer(
    query: str,
    node_content: str,
    traversal_path: list,
    provider: str = "ollama",
    model: Optional[str] = None,
    max_length: int = 1000,
) -> str:
    """
    Generate an answer using LLM based on selected node content.
    
    Args:
        query: User's original query.
        node_content: Content of the best-matched node.
        traversal_path: Path from root to selected node.
        provider: "ollama" or "groq".
        model: Optional model name.
        max_length: Maximum answer length (approximate).
    
    Returns:
        Generated answer as a string.
    """
    path_str = " > ".join(traversal_path)
    
    prompt = f"""You are a system design expert. Answer the user's question based on the provided knowledge base content.

User Question: "{query}"

Knowledge Base Path: {path_str}

Relevant Content:
{node_content}

Generate a clear, direct answer to the user's question using the provided content.
Keep the answer concise (around {max_length} characters).
If the content doesn't fully answer the question, provide your best explanation based on it."""

    response = call_llm(prompt, provider=provider, model=model)
    
    # Trim if too long
    if len(response) > max_length * 1.5:
        response = response[: max_length] + " ..."
    
    return response.strip()


def generate_summary(
    content: str,
    max_length: int = 500,
    provider: str = "ollama",
    model: Optional[str] = None,
) -> str:
    """
    Generate a concise summary of long content.
    
    Args:
        content: The content to summarize.
        max_length: Maximum summary length.
        provider: "ollama" or "groq".
        model: Optional model name.
    
    Returns:
        Summarized content.
    """
    prompt = f"""Summarize the following system design content in {max_length} characters or less:

{content}

Provide a concise summary highlighting the key points."""

    response = call_llm(prompt, provider=provider, model=model)
    
    if len(response) > max_length * 1.5:
        response = response[: max_length] + " ..."
    
    return response.strip()


def extract_excerpt(content: str, max_length: int = 500) -> str:
    """
    Extract a representative excerpt from content (no LLM call).
    
    Args:
        content: The content to excerpt.
        max_length: Maximum excerpt length.
    
    Returns:
        Excerpt of content.
    """
    if len(content) <= max_length:
        return content
    
    # Find a good break point
    truncated = content[: max_length]
    
    # Try to end at a sentence boundary
    last_period = truncated.rfind(".")
    if last_period > max_length * 0.7:
        return truncated[: last_period + 1]
    
    # Otherwise, end at a word boundary
    last_space = truncated.rfind(" ")
    if last_space > 0:
        return truncated[: last_space] + " ..."
    
    return truncated + " ..."


if __name__ == "__main__":
    # Test
    test_content = """
Consistent hashing is a technique used to distribute data across multiple servers.
It maps both data keys and servers to points on a hash ring, so that each key is
stored on the server whose point is nearest to it on the ring. When a server is
added or removed, only a fraction of keys need to be remapped, making it ideal
for distributed caching and databases.
    """.strip()
    
    test_query = "What is consistent hashing?"
    test_path = ["System Design", "Caching", "Consistent Hashing"]
    
    print("Excerpt:")
    print(extract_excerpt(test_content, 200))
    print()
    
    print("Trying LLM-based summary...")
    try:
        summary = generate_summary(test_content, 200, provider="ollama")
        print(f"Summary: {summary}")
    except Exception as e:
        print(f"Error: {e}")
