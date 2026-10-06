"""Avatar/UGC prompt engine.

Two paths:
  - `build_local_prompt(spec)` → deterministic English photorealistic prompt
    assembled directly from the structured avatar spec. No API required.
  - `build_ai_prompt(ai_service, spec)` → sends the local prompt + spec to
    an LLM (Gemini or Groq free tier) which rewrites + enriches it. Returns
    `(prompt_text, token_usage_dict)`.
"""
from typing import Dict, Any, Tuple

AVATAR_FIELD_LABELS = {
    "gender": "Gender",
    "age_range": "Age range",
    "ethnicity": "Ethnicity",
    "skin_tone": "Skin tone",
    "hijab": "Hijab",
    "hair_style": "Hair style",
    "hair_color": "Hair color",
    "grooming": "Grooming",
    "expression": "Expression",
    "glasses": "Glasses",
    "body_pose": "Body pose",
    "framing": "Framing",
    "hand_gesture": "Hand gesture",
    "outfit": "Outfit",
    "outfit_color": "Outfit color",
    "setting": "Setting",
    "lighting": "Lighting",
    "style": "Style",
    "aspect_ratio": "Aspect ratio",
    "extras": "Extra details",
}

DEFAULT_NEGATIVE = (
    "no distorted faces, no extra fingers, no watermark, no logo overlays, "
    "no AI-generated plastic look, no overly airbrushed skin, no artificial "
    "studio lighting, no stock-footage framing, no censored content."
)


def _val(spec: Dict[str, Any], k: str, fallback: str = "") -> str:
    v = (spec.get(k) or "").strip()
    if not v or v.lower() == "auto":
        return fallback
    return v


def build_local_prompt(spec: Dict[str, Any], product: Dict[str, Any] | None = None) -> str:
    """Deterministic photorealistic prompt, assembled in English."""
    gender    = _val(spec, "gender", "person")
    age       = _val(spec, "age_range", "mid-20s")
    ethnicity = _val(spec, "ethnicity", "Southeast Asian")
    skin      = _val(spec, "skin_tone", "natural warm")

    hijab     = _val(spec, "hijab")
    hair_s    = _val(spec, "hair_style", "shoulder-length")
    hair_c    = _val(spec, "hair_color", "natural black")
    grooming  = _val(spec, "grooming", "natural, minimal makeup")
    expr      = _val(spec, "expression", "warm friendly smile")
    glasses   = _val(spec, "glasses")

    pose      = _val(spec, "body_pose", "sitting")
    framing   = _val(spec, "framing", "chest-up talking head")
    gesture   = _val(spec, "hand_gesture", "natural hand gesture")

    outfit    = _val(spec, "outfit", "plain t-shirt")
    outfit_c  = _val(spec, "outfit_color")

    setting   = _val(spec, "setting", "warm living room")
    lighting  = _val(spec, "lighting", "soft natural window light")
    style     = _val(spec, "style", "photorealistic UGC")
    aspect    = _val(spec, "aspect_ratio", "9:16")
    extras    = _val(spec, "extras")

    # Subject sentence
    appearance = f"{gender}, around {age}, {ethnicity}"
    if skin: appearance += f", with {skin} skin tone"

    if hijab and hijab.lower() not in ("tanpa hijab", "none", "no hijab"):
        hair_desc = f"wearing a {hijab}"
    else:
        hair_desc = f"with {hair_s} {hair_c} hair"

    face_desc = f"{grooming}, {expr}"
    if glasses and glasses.lower() not in ("tanpa kacamata", "none", "no glasses"):
        face_desc += f", wearing {glasses}"

    pose_desc = f"{pose}, {framing} framing, {gesture}"

    outfit_desc = f"wearing a {outfit_c + ' ' if outfit_c else ''}{outfit}"

    setting_desc = f"Setting: a {setting}, {lighting}"

    # Authentic UGC qualifier
    qualifier = ("Authentic amateur iPhone front-camera snapshot, candid and unposed, "
                 "but the person is naturally attractive and photogenic. Clear healthy skin "
                 "with visible pores and soft fine texture, a soft natural glow (realistic, "
                 "NOT airbrushed or plastic), a few soft flyaway hairs, true-to-life colors "
                 "and natural proportions.")

    header = f"{style} candid vertical UGC portrait in {aspect} aspect ratio, {framing}."
    body = f"A {appearance}, {hair_desc}, {face_desc}, {pose_desc}. {outfit_desc}. {setting_desc}. "

    # Product mention
    if product and product.get("name"):
        prod_line = f"The person is holding and showing the product: {product['name']}"
        if product.get("description"):
            prod_line += f" — {product['description']}"
        prod_line += ". The product is clearly visible, naturally held near the chest/face level, "
        prod_line += "with the camera focus on both the person and the product."
        body += prod_line + " "

    body += qualifier
    if extras:
        body += f" Additional details: {extras}."

    # Languages: spec["languages"] may be a list or a comma-string
    raw_langs = spec.get("languages")
    langs: list[str] = []
    if isinstance(raw_langs, list):
        langs = [str(l).strip() for l in raw_langs if l]
    elif isinstance(raw_langs, str) and raw_langs.strip():
        langs = [l.strip() for l in raw_langs.split(",") if l.strip()]
    if langs:
        body += f" The person speaks: {', '.join(langs)}."

    return f"{header}\n\n{body}"


def build_ai_prompt(ai_call, spec: Dict[str, Any],
                     product: Dict[str, Any] | None = None) -> Tuple[str, Dict[str, int]]:
    """Use an LLM to rewrite+translate the structured spec into a rich English prompt.

    `ai_call(prompt: str) -> {text, input_tokens, output_tokens, total_tokens}`.
    Returns (prompt_text, token_dict).
    """
    local = build_local_prompt(spec, product)
    instruction = (
        "You are a prompt engineer for a text-to-image / text-to-video model that produces "
        "photorealistic UGC-style content. Rewrite the DRAFT below into a single tight English "
        "prompt (one paragraph, under 160 words) that preserves every attribute and adds the "
        "rendering keywords a photorealistic model needs (natural lighting, pore detail, candid "
        "amateur phone photography, no artificial retouch). Translate any Indonesian/local terms. "
        "Return ONLY the prompt text, no code fences, no commentary.\n\nDRAFT:\n" + local
    )
    result = ai_call(instruction)
    text = (result.get("text") or "").strip()
    if not text:
        return local, {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    return text, {
        "input_tokens": result.get("input_tokens", 0),
        "output_tokens": result.get("output_tokens", 0),
        "total_tokens": result.get("total_tokens", 0),
    }
