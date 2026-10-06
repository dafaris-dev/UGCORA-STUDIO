"""Google Gemini integration via official REST endpoint (v1beta generateContent).

Uses httpx so no extra SDK is required. The model is configurable at runtime.
"""
import base64
import json
import logging
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List

import httpx

logger = logging.getLogger(__name__)

GEMINI_API_ROOT = "https://generativelanguage.googleapis.com/v1beta"


class GeminiError(Exception):
    pass


def _endpoint(model: str) -> str:
    return f"{GEMINI_API_ROOT}/models/{model}:generateContent"


def _build_parts(prompt: str, image_path: Optional[str] = None) -> List[Dict[str, Any]]:
    parts: List[Dict[str, Any]] = [{"text": prompt}]
    if image_path:
        p = Path(image_path)
        if p.exists():
            mime, _ = mimetypes.guess_type(str(p))
            if not mime:
                mime = "image/jpeg"
            data = base64.b64encode(p.read_bytes()).decode("ascii")
            parts.append({"inline_data": {"mime_type": mime, "data": data}})
    return parts


def _call(api_key: str, model: str, prompt: str, image_path: Optional[str] = None,
          json_mode: bool = False, temperature: float = 0.7) -> str:
    if not api_key:
        raise GeminiError("Gemini API key is not configured.")
    if not model:
        raise GeminiError("Gemini model is not configured.")

    payload: Dict[str, Any] = {
        "contents": [{"role": "user", "parts": _build_parts(prompt, image_path)}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 2048,
        },
    }
    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    url = _endpoint(model)
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, params={"key": api_key}, json=payload)
    except httpx.HTTPError as exc:
        logger.exception("Gemini HTTP error")
        raise GeminiError(f"Network error contacting Gemini: {exc}") from exc

    if resp.status_code != 200:
        try:
            data = resp.json()
            msg = data.get("error", {}).get("message", resp.text)
        except Exception:
            msg = resp.text
        raise GeminiError(f"Gemini API error ({resp.status_code}): {msg}")

    try:
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise GeminiError("Gemini returned no candidates.")
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        text_out = "".join(p.get("text", "") for p in parts)
        return text_out.strip()
    except GeminiError:
        raise
    except Exception as exc:
        raise GeminiError(f"Unexpected Gemini response: {exc}") from exc


def _safe_json(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    text = text.strip()
    if text.startswith("```"):
        # Strip code fence
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        # Try to find first JSON object substring
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except Exception:
                pass
    return {"raw": text}


# ---------- Public API ----------

def test_connection(api_key: str, model: str) -> Dict[str, Any]:
    try:
        out = _call(api_key, model, "Reply with the single word: OK", temperature=0.0)
        return {"ok": True, "model": model, "response": out[:200]}
    except GeminiError as exc:
        return {"ok": False, "error": str(exc)}


def analyze_product(api_key: str, model: str, product: Dict[str, Any], image_path: Optional[str] = None) -> Dict[str, Any]:
    prompt = f"""You are a senior UGC marketing strategist.
Analyze this product and return a strict JSON object (no prose, no code fences).

Product name: {product.get("name", "")}
Description: {product.get("description", "")}
Benefits: {product.get("benefits", "")}
Target audience hint: {product.get("target_audience", "")}
Website: {product.get("website", "")}
CTA hint: {product.get("cta", "")}

Return keys:
category (short string),
target_audience (one paragraph),
customer_problem (one paragraph),
main_benefits (bullet-style single string with newlines),
usp (one sentence),
marketing_angle (one paragraph),
ugc_hook (a punchy opening line a creator would say),
recommended_cta (one short line).
"""
    text = _call(api_key, model, prompt, image_path=image_path, json_mode=True, temperature=0.6)
    return _safe_json(text)


def generate_hooks(api_key: str, model: str, product_name: str, audience: str, n: int = 5) -> List[str]:
    prompt = f"""Write {n} short, authentic UGC video opening hooks (first spoken line)
for the product "{product_name}" targeting {audience}.
Return a strict JSON array of strings only."""
    text = _call(api_key, model, prompt, json_mode=True, temperature=0.9)
    data = _safe_json(text)
    if isinstance(data, list):
        return [str(x) for x in data]
    if isinstance(data, dict) and "hooks" in data:
        return [str(x) for x in data["hooks"]]
    return [str(data.get("raw", ""))] if data else []


def generate_cta(api_key: str, model: str, product_name: str, website: str = "") -> str:
    prompt = f"""Write ONE short, natural UGC call-to-action line (max 15 words)
for the product "{product_name}". Website: {website or 'n/a'}.
Avoid corporate language. Return plain text only."""
    return _call(api_key, model, prompt, temperature=0.8)


def generate_script(api_key: str, model: str, context: Dict[str, Any]) -> Dict[str, Any]:
    prompt = f"""You are writing a UGC video script that must sound like a real creator,
NOT a corporate ad. Avoid robotic or formal wording. Keep it conversational.

Product: {context.get("product_name", "")}
Product benefits: {context.get("product_benefits", "")}
Target audience: {context.get("target_audience", "")}
Creator persona: {context.get("creator_name", "")} — {context.get("creator_personality", "")}
Marketing angle: {context.get("marketing_angle", "")}
Template: {context.get("template", "Problem → Solution")}
Tone: {context.get("tone", "Casual")}
Duration: {context.get("duration_seconds", 30)} seconds
Call to action: {context.get("cta", "")}

Return a strict JSON object with keys:
hook (one punchy opening line),
body (the main spoken script, written as if speaking, 2-5 short paragraphs),
cta (one short natural call-to-action line),
full_text (hook + body + cta joined with blank lines).
"""
    text = _call(api_key, model, prompt, json_mode=True, temperature=0.85)
    data = _safe_json(text)
    if "full_text" not in data:
        parts = [data.get("hook", ""), data.get("body", ""), data.get("cta", "")]
        data["full_text"] = "\n\n".join(p for p in parts if p)
    return data


def rewrite_script(api_key: str, model: str, script_text: str, instruction: str) -> str:
    prompt = f"""Rewrite this UGC script per the instruction. Keep it natural, conversational,
and under the same duration. Return plain text only.

INSTRUCTION:
{instruction}

ORIGINAL SCRIPT:
{script_text}
"""
    return _call(api_key, model, prompt, temperature=0.8)


def generate_video_prompt(api_key: str, model: str, context: Dict[str, Any]) -> str:
    """Build a detailed production prompt via Gemini, structured for a video model."""
    prompt = f"""Build a detailed structured prompt for a text-to-video model that will
generate a vertical UGC-style video. Use the sections exactly as named below,
each on its own line prefixed by the heading in ALL CAPS followed by a colon.

Context:
Product: {context.get("product_name", "")}
Product description: {context.get("product_description", "")}
Benefits: {context.get("product_benefits", "")}
Creator: {context.get("creator_name", "")} ({context.get("creator_personality", "")})
Location: {context.get("location", "")}
Camera: {context.get("camera", "")}
Lighting: {context.get("lighting", "")}
Action: {context.get("action", "")}
Script dialogue: {context.get("script", "")}
Voice style: {context.get("voice", "")}
Marketing angle: {context.get("marketing_angle", "")}
Format: {context.get("aspect_ratio", "9:16")} {context.get("resolution", "1080p")}
CTA: {context.get("cta", "")}

Required sections:
SUBJECT, ENVIRONMENT, CREATOR, PRODUCT, ACTION, CAMERA, LIGHTING, DIALOGUE,
EMOTION, PRODUCT INTERACTION, MARKETING INTENT, CTA, NEGATIVE INSTRUCTIONS.

Keep each section concise (1-3 sentences). Return plain text only — no code fences.
"""
    return _call(api_key, model, prompt, temperature=0.6)
