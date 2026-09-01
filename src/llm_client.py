import os
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://10.5.30.32:11434")
MODEL = os.getenv("OLLAMA_MODEL", "gemma4:12b")


def call_llm(prompt: str, temperature: float = 0.1, max_tokens: int = 2048) -> str:
    url = f"{OLLAMA_HOST}/api/generate"

    base_payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "top_p": 0.9
        }
    }

    # Try JSON mode first
    payload = dict(base_payload)
    payload["format"] = "json"

    try:
        response = requests.post(url, json=payload, timeout=600)
        response.raise_for_status()
        data = response.json()
        out = data.get("response", "")
        if out.strip():
            return out
    except Exception:
        pass

    # Fallback normal generation
    response = requests.post(url, json=base_payload, timeout=600)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")