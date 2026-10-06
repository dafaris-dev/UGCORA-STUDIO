"""Groq integration — free-tier LLM used as an alternative to Gemini
for prompt building and translation. Returns token counts.
"""
import json
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqError(Exception):
    pass


def _call(api_key: str, model: str, prompt: str, system: Optional[str] = None,
          temperature: float = 0.7, json_mode: bool = False) -> Dict[str, Any]:
    if not api_key:
        raise GroqError("Groq API key is not configured.")
    if not model:
        raise GroqError("Groq model is not configured.")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 2048,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    try:
        with httpx.Client(timeout=60.0) as c:
            r = c.post(GROQ_URL, json=body, headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            })
    except httpx.HTTPError as exc:
        raise GroqError(f"Network error contacting Groq: {exc}") from exc

    if r.status_code != 200:
        try:
            msg = r.json().get("error", {}).get("message", r.text)
        except Exception:
            msg = r.text
        raise GroqError(f"Groq API error ({r.status_code}): {msg}")

    data = r.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except Exception as exc:
        raise GroqError(f"Unexpected Groq response: {exc}") from exc
    usage = data.get("usage", {})
    return {
        "text": text.strip(),
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
    }


def test_connection(api_key: str, model: str) -> Dict[str, Any]:
    try:
        out = _call(api_key, model, "Reply with the single word: OK", temperature=0.0)
        return {"ok": True, "model": model, "response": out["text"][:200]}
    except GroqError as exc:
        return {"ok": False, "error": str(exc)}
