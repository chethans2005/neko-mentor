"""
setup_check.py — Validate the environment and dependencies.

Checks:
  1. Knowledge base file exists and is valid JSON
  2. Required Python packages are installed
  3. Environment variables are configured
  4. Backend modules can be imported
  5. LLM providers (Ollama/Groq) are accessible
"""

import json
import os
import sys
import subprocess

# Add backend/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ============================================================================
# CHECKS
# ============================================================================

def check_kb_file(kb_path: str) -> tuple:
    """Check if KB file exists and is valid JSON."""
    print(f"\n1. Checking knowledge base file...")
    print(f"   Path: {kb_path}")
    
    if not os.path.exists(kb_path):
        return False, f"KB file not found: {kb_path}"
    
    try:
        with open(kb_path, "r") as f:
            kb = json.load(f)
        
        node_count = len(kb)
        print(f"   ✓ KB file valid ({node_count} nodes)")
        return True, "KB file valid"
    except json.JSONDecodeError as e:
        return False, f"KB file invalid JSON: {e}"
    except Exception as e:
        return False, f"Error reading KB: {e}"


def check_python_packages() -> tuple:
    """Check if required Python packages are installed."""
    print(f"\n2. Checking Python packages...")
    
    required = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "pydantic": "pydantic",
        "requests": "requests",
        "groq": "groq",
        "python-dotenv": "dotenv",
    }
    
    missing = []
    
    for pkg, import_name in required.items():
        try:
            __import__(import_name)
            print(f"   ✓ {pkg}")
        except ImportError:
            print(f"   ✗ {pkg}")
            missing.append(pkg)
    
    if missing:
        return False, f"Missing packages: {', '.join(missing)}"
    
    return True, "All packages installed"


def check_environment_variables() -> tuple:
    """Check if important environment variables are set."""
    print(f"\n3. Checking environment variables...")
    
    vars_to_check = {
        "LLM_PROVIDER": ("optional", "ollama"),
        "OLLAMA_BASE_URL": ("optional", "http://localhost:11434"),
        "GROQ_API_KEY": ("optional", "not set"),
    }
    
    all_ok = True
    
    for var, (req_type, default) in vars_to_check.items():
        value = os.getenv(var)
        if value:
            print(f"   ✓ {var}={value}")
        else:
            if req_type == "required":
                print(f"   ✗ {var} not set (REQUIRED)")
                all_ok = False
            else:
                print(f"   ℹ {var} not set (using {default})")
    
    return all_ok, "Environment variables checked"


def check_backend_imports() -> tuple:
    """Check if backend modules can be imported."""
    print(f"\n4. Checking backend module imports...")
    
    modules = ["llm", "query_analyzer", "navigator", "answer_generator"]
    
    failed = []
    
    for mod in modules:
        try:
            __import__(mod)
            print(f"   ✓ {mod}")
        except ImportError as e:
            print(f"   ✗ {mod}: {e}")
            failed.append(mod)
    
    if failed:
        return False, f"Failed to import: {', '.join(failed)}"
    
    return True, "All modules importable"


def check_ollama() -> tuple:
    """Check if Ollama is running."""
    print(f"\n5. Checking Ollama availability...")
    
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    try:
        import requests
        response = requests.get(f"{base_url}/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m.get("name") for m in models]
            print(f"   ✓ Ollama running at {base_url}")
            print(f"   ✓ Available models: {', '.join(model_names[:3])}")
            return True, f"Ollama available ({len(models)} models)"
        else:
            return False, f"Ollama responded with status {response.status_code}"
    except requests.exceptions.ConnectionError:
        print(f"   ℹ Ollama not running at {base_url}")
        return False, "Ollama not running (optional for Groq mode)"
    except Exception as e:
        return False, f"Error checking Ollama: {e}"


def check_groq() -> tuple:
    """Check if Groq API key is set and valid."""
    print(f"\n6. Checking Groq API key...")
    
    api_key = os.getenv("GROQ_API_KEY", "")
    
    if not api_key:
        print(f"   ℹ GROQ_API_KEY not set")
        return False, "Groq API key not set (optional)"
    
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        # Try to list models (lightweight check)
        models = client.models.list()
        print(f"   ✓ Groq API key valid")
        print(f"   ✓ Groq available")
        return True, "Groq ready"
    except Exception as e:
        return False, f"Groq error: {e}"


def check_main_import() -> tuple:
    """Check if main.py can be imported."""
    print(f"\n7. Checking FastAPI server import...")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
        import main
        print(f"   ✓ main.py imports successfully")
        return True, "FastAPI server ready"
    except Exception as e:
        return False, f"main.py import failed: {e}"


# ============================================================================
# MAIN
# ============================================================================

def run_all_checks():
    """Run all setup checks."""
    print("\n" + "="*70)
    print("VECTORLESS SYSTEM DESIGN ASSISTANT - SETUP CHECK")
    print("="*70)
    
    kb_path = os.getenv("KB_PATH", "shared/data/kb/knowledge_base.json")
    
    checks = [
        ("KB File", check_kb_file, (kb_path,)),
        ("Python Packages", check_python_packages, ()),
        ("Environment", check_environment_variables, ()),
        ("Backend Modules", check_backend_imports, ()),
        ("Ollama", check_ollama, ()),
        ("Groq", check_groq, ()),
        ("FastAPI", check_main_import, ()),
    ]
    
    results = {}
    for name, check_fn, args in checks:
        try:
            status, message = check_fn(*args)
            results[name] = (status, message)
        except Exception as e:
            results[name] = (False, f"Check error: {e}")
    
    # Summary
    print(f"\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    passed = sum(1 for status, _ in results.values() if status)
    total = len(results)
    
    for name, (status, message) in results.items():
        symbol = "✓" if status else "✗"
        print(f"{symbol} {name}: {message}")
    
    print(f"\n{passed}/{total} checks passed")
    
    # Overall status
    all_passed = all(status for status, _ in results.values())
    
    if all_passed:
        print("\n✓ Setup is complete! You're ready to go.")
        print("  Run: python cli_test.py \"Your question here\"")
        return 0
    else:
        print("\n✗ Some checks failed. Please review the output above.")
        print("  To install missing packages: pip install -r requirements.txt")
        return 1


if __name__ == "__main__":
    exit_code = run_all_checks()
    sys.exit(exit_code)
