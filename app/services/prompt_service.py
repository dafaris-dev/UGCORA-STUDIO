"""Local prompt engine - deterministic fallback that produces a structured
production prompt without requiring a model call. Also used to validate
Gemini-produced prompts."""
from typing import Dict, Any

SECTIONS = [
    "SUBJECT",
    "ENVIRONMENT",
    "CREATOR",
    "PRODUCT",
    "ACTION",
    "CAMERA",
    "LIGHTING",
    "DIALOGUE",
    "EMOTION",
    "PRODUCT INTERACTION",
    "MARKETING INTENT",
    "CTA",
    "NEGATIVE INSTRUCTIONS",
]

DEFAULT_NEGATIVE = (
    "no distorted faces, no extra fingers, no watermark, no logo overlays, "
    "no corporate stock-footage look, no ad-like staging, no unnatural lip-sync, "
    "no low resolution artifacts, no censored content."
)


def build_prompt(ctx: Dict[str, Any]) -> str:
    """Build a structured production prompt from a context dict."""
    name = ctx.get("product_name", "the product")
    sections = {
        "SUBJECT": f"A user-generated-content style short video about {name}.",
        "ENVIRONMENT": ctx.get("location", "modern bedroom with soft natural light"),
        "CREATOR": f"{ctx.get('creator_name', 'friendly young creator')} — "
                   f"{ctx.get('creator_personality', 'warm, casual, authentic')}, "
                   f"{ctx.get('creator_age', 'natural age appearance')}, "
                   f"wearing {ctx.get('clothing', 'casual everyday clothes')}.",
        "PRODUCT": f"{name}. {ctx.get('product_description', '')} "
                   f"Key benefits: {ctx.get('product_benefits', '')}",
        "ACTION": ctx.get("action", "creator holding the product up to camera "
                                     "and talking directly to the viewer."),
        "CAMERA": ctx.get("camera", "phone selfie, handheld, eye-level framing, slight natural shake"),
        "LIGHTING": ctx.get("lighting", "soft natural window light, warm key, no harsh shadows"),
        "DIALOGUE": ctx.get("script", ""),
        "EMOTION": ctx.get("emotion", "genuine, excited, relaxed, trustworthy"),
        "PRODUCT INTERACTION": ctx.get("product_interaction",
                                       "creator demonstrates the product naturally, "
                                       "showing it close to the lens for one beat."),
        "MARKETING INTENT": ctx.get("marketing_angle", ""),
        "CTA": ctx.get("cta", ""),
        "NEGATIVE INSTRUCTIONS": ctx.get("negative_prompt") or DEFAULT_NEGATIVE,
    }
    aspect = ctx.get("aspect_ratio", "9:16")
    resolution = ctx.get("resolution", "1080p")
    duration = ctx.get("duration_seconds", 30)
    header = f"[FORMAT: {aspect} • {resolution} • ~{duration}s UGC vertical video]\n"
    out = [header]
    for s in SECTIONS:
        out.append(f"{s}: {sections.get(s, '').strip()}")
    return "\n".join(out)
