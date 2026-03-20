import requests

def clean_text(text):
    prompt = f"""
Convert this into structured system design notes:
- Definition
- How it works
- Pros/Cons
- Use cases

{text[:2000]}
"""

    res = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "mistral",
            "prompt": prompt,
            "stream": False
        }
    )

    return res.json()["response"]