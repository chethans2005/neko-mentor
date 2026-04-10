"""
llm.py — LLM abstraction layer supporting Ollama (local) and Groq (API).

Provides a simple interface:
    result = call_llm(prompt, model="llama3.1", provider="ollama")
"""

import json
import os
from dotenv import load_dotenv
import secrets_manager
from typing import Optional, Literal
import requests
from groq import Groq as GroqClient
import asyncio

try:
    import httpx
except Exception:
    httpx = None


# ============================================================================
# CONFIGURATION
# ============================================================================

# Load .env files (try backend/config/.env first, then any .env in cwd)
_THIS_DIR = os.path.dirname(__file__)
_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_ENV_PATHS = [
    os.path.join(_ROOT, "config", ".env"),
    os.path.join(os.getcwd(), ".env"),
]
for _p in _ENV_PATHS:
    try:
        load_dotenv(_p)
    except Exception:
        pass

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
DEFAULT_MODEL_OLLAMA = os.getenv("OLLAMA_MODEL", "llama3.1")
DEFAULT_MODEL_GROQ = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")


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


async def call_ollama_async(prompt: str, model: str = DEFAULT_MODEL_OLLAMA) -> str:
    """Async Ollama call using httpx. Falls back to sync `requests` if httpx
    is unavailable by running the sync call in a thread.
    """
    if httpx is None:
        # httpx not installed; run sync function in thread
        return await asyncio.to_thread(call_ollama, prompt, model)

    url = f"{OLLAMA_BASE_URL}/api/generate"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                json={"model": model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            result = resp.json()
            return result.get("response", "").strip()
    except httpx.ConnectError:
        raise RuntimeError(
            f"Failed to connect to Ollama at {OLLAMA_BASE_URL}. Is Ollama running? (ollama serve)"
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
    # Retrieve API key from secret provider (env or backend/config/.env)
    api_key = secrets_manager.get_secret("GROQ_API_KEY", required=True)
    try:
        client = GroqClient(api_key=api_key)
        # Use the Chat Completions endpoint available on the Groq client
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_completion_tokens=2048,
        )

        # Defensive extraction of the returned text
        try:
            text = resp.choices[0].message.content
        except Exception:
            try:
                text = resp["choices"][0]["message"]["content"]
            except Exception:
                text = str(resp)

        return (text or "").strip()
    except Exception as e:
        raise RuntimeError(f"Groq API error: {str(e)}")


async def call_groq_async(prompt: str, model: str = DEFAULT_MODEL_GROQ) -> str:
    """Async wrapper for Groq client. The Groq Python client is synchronous,
    so run it in a thread to avoid blocking the event loop.
    """
    return await asyncio.to_thread(call_groq, prompt, model)


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


async def call_llm_async(
    prompt: str,
    model: Optional[str] = None,
    provider: Optional[Literal["ollama", "groq"]] = None,
) -> str:
    """Async entrypoint for calling LLMs. Uses async HTTP for Ollama when
    available and threads for sync clients otherwise.
    """
    if provider is None:
        provider = DEFAULT_PROVIDER

    if provider == "ollama":
        if model is None:
            model = DEFAULT_MODEL_OLLAMA
        return await call_ollama_async(prompt, model)
    elif provider == "groq":
        if model is None:
            model = DEFAULT_MODEL_GROQ
        return await call_groq_async(prompt, model)
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
        # Try to extract JSON-like content anywhere in the text by
        # locating the first '{' and finding the matching '}' taking
        # nesting into account.
        s = text
        start_idx = s.find("{")
        if start_idx == -1:
            return {}

        depth = 0
        for i in range(start_idx, len(s)):
            c = s[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    candidate = s[start_idx : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        # If parsing fails, continue searching for next '{'
                        next_start = s.find("{", start_idx + 1)
                        if next_start == -1:
                            return {}
                        start_idx = next_start
                        depth = 0
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
