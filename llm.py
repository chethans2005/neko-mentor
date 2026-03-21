"""
llm.py — LLM abstraction layer supporting Ollama (local) and Groq (API).

Provides a simple interface:
    result = call_llm(prompt, model="llama3.1", provider="ollama")
"""

import json
import os
from typing import Optional, Literal
import requests
from groq import Groq as GroqClient


# ============================================================================
# CONFIGURATION
# ============================================================================

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
DEFAULT_MODEL_OLLAMA = os.getenv("OLLAMA_MODEL", "llama3.1")
DEFAULT_MODEL_GROQ = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")


# ============================================================================
# OLLAMA CLIENT
# ============================================================================

def call_ollama(prompt: str, model: str = DEFAULT_MODEL_OLLAMA) -> str:
    """
    Call Ollama API (local LLM).
    
    Args:
        prompt: The prompt to send to the model.
        model: Model name (default: llama3.1).
    
    Returns:
        The model's response as a string.
    
    Raises:
        RuntimeError: If Ollama is not accessible.
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    
    try:
        response = requests.post(
            url,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "").strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Failed to connect to Ollama at {OLLAMA_BASE_URL}. "
            "Is Ollama running? (ollama serve)"
        )
    except Exception as e:
        raise RuntimeError(f"Ollama API error: {str(e)}")


# ============================================================================
# GROQ CLIENT
# ============================================================================

def call_groq(prompt: str, model: str = DEFAULT_MODEL_GROQ) -> str:
    """
    Call Groq API (cloud-based LLM).
    
    Args:
        prompt: The prompt to send to the model.
        model: Model name (default: mixtral-8x7b-32768).
    
    Returns:
        The model's response as a string.
    
    Raises:
        RuntimeError: If GROQ_API_KEY is not set or API call fails.
    """
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY environment variable not set. "
            "Set it or use provider='ollama'."
        )
    
    try:
        client = GroqClient(api_key=GROQ_API_KEY)
        message = client.messages.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
        )
        return message.content[0].text.strip()
    except Exception as e:
        raise RuntimeError(f"Groq API error: {str(e)}")


# ============================================================================
# UNIFIED INTERFACE
# ============================================================================

def call_llm(
    prompt: str,
    model: Optional[str] = None,
    provider: Optional[Literal["ollama", "groq"]] = None,
) -> str:
    """
    Call an LLM with a prompt.
    
    Args:
        prompt: The prompt to send.
        model: Model name. If None, uses default for the provider.
        provider: "ollama" or "groq". If None, uses DEFAULT_PROVIDER.
    
    Returns:
        The LLM's response as a string.
    
    Raises:
        RuntimeError: If the provider is unavailable.
    """
    if provider is None:
        provider = DEFAULT_PROVIDER
    
    if provider == "ollama":
        if model is None:
            model = DEFAULT_MODEL_OLLAMA
        return call_ollama(prompt, model)
    elif provider == "groq":
        if model is None:
            model = DEFAULT_MODEL_GROQ
        return call_groq(prompt, model)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def parse_json_response(text: str) -> dict:
    """
    Extract and parse JSON from LLM response.
    Falls back to empty dict if parsing fails.
    
    Args:
        text: The LLM response text.
    
    Returns:
        Parsed JSON dict, or empty dict if parsing fails.
    """
    try:
        # Try direct parsing first
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON-like content
        # Look for {...} or [{...}]
        text = text.strip()
        if text.startswith("{"):
            # Find matching closing brace
            depth = 0
            for i, char in enumerate(text):
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[: i + 1])
                        except json.JSONDecodeError:
                            pass
                        break
        
        # Fallback: return empty dict
        return {}


if __name__ == "__main__":
    # Simple test
    print("Testing LLM interface...")
    
    # Test with provider selection
    try:
        result = call_llm("Say 'Hello, World!' in exactly 2 words.", provider="ollama")
        print(f"Ollama: {result}")
    except RuntimeError as e:
        print(f"Ollama error: {e}")
    
    try:
        result = call_llm("Say 'Hello, API!' in exactly 2 words.", provider="groq")
        print(f"Groq: {result}")
    except RuntimeError as e:
        print(f"Groq error: {e}")
