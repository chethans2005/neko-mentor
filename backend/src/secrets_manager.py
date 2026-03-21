"""
secrets_manager.py — simple secret access abstraction.

Provides `get_secret(name, default=None, required=False)` which prefers
environment variables and falls back to loading `backend/config/.env` if
present. Designed to centralize secret access so production secret backends
can be swapped in later (Vault, AWS Secrets Manager, etc.).
"""
import os
from dotenv import load_dotenv
from typing import Optional


def _load_local_dotenv():
    """Load `backend/config/.env` if present (no-op if already loaded)."""
    try:
        this_dir = os.path.dirname(__file__)
        root = os.path.abspath(os.path.join(this_dir, ".."))
        env_path = os.path.join(root, "config", ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path)
    except Exception:
        # Best-effort; do not fail on dotenv errors
        pass


def get_secret(name: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """
    Retrieve a secret value.

    Order of preference:
    1. OS environment variables
    2. `backend/config/.env` (if present)
    3. `default` argument

    If `required` is True and no value is found, raises RuntimeError.
    """
    # Prefer already-present environment variables
    val = os.environ.get(name)
    if val:
        return val

    # Try loading local dotenv and re-check
    _load_local_dotenv()
    val = os.environ.get(name)
    if val:
        return val

    if default is not None:
        return default

    if required:
        raise RuntimeError(f"Required secret '{name}' not found in environment or config/.env")

    return None
