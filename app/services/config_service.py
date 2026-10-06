"""Runtime configuration helpers: reads from env, with DB overrides.

Provider catalog is defined here so routes/settings/templates can share it.
No API keys are ever hard-coded; everything is user-entered.
"""
import os
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.setting import Setting


# ─────────────────────────────────────────────────────────────────────
# Provider catalog
#
# Each provider lists:
#   key:    short identifier used as the config-key prefix
#   name:   display name
#   badge:  optional {label, kind} where kind ∈ {free, paid, beta, default}
#   models: list of model ids for the "Model Default" dropdown
#   fields: extra config fields beyond API_KEY (dicts: name, label, kind)
#   help:   user-facing one-liner with sign-up link
#
# For every provider, two settings keys are always valid:
#   <KEY>_API_KEY, <KEY>_MODEL
# Extra fields produce keys like <KEY>_<FIELD-NAME-UPPER>.
# ─────────────────────────────────────────────────────────────────────

LLM_PROVIDERS: List[Dict[str, Any]] = [
    {"key": "anthropic", "name": "Anthropic",
     "models": ["claude-sonnet-4-5", "claude-opus-4-5", "claude-haiku-4-5"],
     "help": 'Paling bagus untuk nulis script natural. Key: console.anthropic.com. Berbayar (pay-as-you-go).'},
    {"key": "openai", "name": "OpenAI",
     "models": ["gpt-5", "gpt-4o", "gpt-4o-mini", "o1"],
     "help": "Key: platform.openai.com/api-keys. Berbayar."},
    {"key": "gemini", "name": "Google Gemini", "badge": {"label": "FREE", "kind": "free"},
     "models": ["gemini-2.0-flash", "gemini-2.0-pro", "gemini-1.5-flash", "gemini-1.5-pro"],
     "help": "GRATIS tanpa kartu kredit. aistudio.google.com/app/apikey. Free tier 1500 req/hari."},
    {"key": "mistral", "name": "Mistral",
     "models": ["mistral-large-latest", "mistral-medium-latest", "codestral-latest"],
     "help": "console.mistral.ai. Harga lebih murah dari GPT-4."},
    {"key": "groq", "name": "Groq", "badge": {"label": "FREE", "kind": "free"},
     "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"],
     "help": "Inference sangat cepat. console.groq.com/keys."},
    {"key": "xai", "name": "xAI (Grok)",
     "models": ["grok-2", "grok-2-mini"],
     "help": "console.x.ai. Berbayar."},
    {"key": "deepseek", "name": "DeepSeek",
     "models": ["deepseek-chat", "deepseek-reasoner"],
     "help": "Harga paling murah. platform.deepseek.com."},
]

VIDEO_PROVIDERS: List[Dict[str, Any]] = [
    {"key": "nvidia", "name": "NVIDIA (Cosmos)",
     "models": ["nvidia/cosmos-1", "nvidia/cosmos-vid-1"],
     "fields": [{"name": "base_url", "label": "Base URL", "kind": "text",
                 "default": "https://integrate.api.nvidia.com/v1"}],
     "help": "NIM gateway. build.nvidia.com. Beberapa model free tier."},
    {"key": "runway", "name": "Runway", "badge": {"label": "PAID", "kind": "paid"},
     "models": ["gen4_turbo", "gen3a_turbo", "gen3a"],
     "help": "Kualitas text-to-video top. dev.runwayml.com."},
    {"key": "pika", "name": "Pika Labs",
     "models": ["pika-2.0", "pika-1.5"], "help": "Spesialis UGC-style. pika.art."},
    {"key": "luma", "name": "Luma Dream Machine",
     "models": ["ray-2", "ray-1.6", "ray-flash"],
     "help": "Realistic motion. lumalabs.ai."},
    {"key": "kling", "name": "Kling AI",
     "models": ["kling-2.1", "kling-1.6", "kling-1.5"],
     "help": "Character motion kuat. klingai.com."},
    {"key": "veo", "name": "Google Veo",
     "models": ["veo-3", "veo-2"],
     "help": "Veo 3 dengan audio. Via Gemini API atau Vertex AI."},
    {"key": "sora", "name": "OpenAI Sora", "badge": {"label": "PAID", "kind": "paid"},
     "models": ["sora-turbo", "sora-pro"],
     "help": "Butuh akses Sora API dari OpenAI."},
    {"key": "hailuo", "name": "MiniMax Hailuo",
     "models": ["hailuo-02", "hailuo-01"], "help": "minimax.io."},
    {"key": "stability_video", "name": "Stability AI Video",
     "models": ["stable-video-diffusion", "sv3d"], "help": "platform.stability.ai."},
]

VOICE_PROVIDERS: List[Dict[str, Any]] = [
    {"key": "elevenlabs", "name": "ElevenLabs",
     "models": ["eleven_multilingual_v2", "eleven_flash_v2_5", "eleven_turbo_v2_5"],
     "help": "10k char/bulan gratis. elevenlabs.io."},
    {"key": "openai_tts", "name": "OpenAI TTS",
     "models": ["tts-1-hd", "tts-1", "gpt-4o-mini-tts"],
     "help": "Pakai OpenAI API key yang sama."},
    {"key": "playht", "name": "PlayHT",
     "models": ["Play3.0-mini", "PlayHT2.0-turbo"],
     "fields": [{"name": "user_id", "label": "User ID", "kind": "text"}],
     "help": "play.ht/studio/api-access."},
    {"key": "cartesia", "name": "Cartesia",
     "models": ["sonic-2", "sonic-turbo"], "help": "Latency rendah. cartesia.ai."},
    {"key": "google_tts", "name": "Google Cloud TTS",
     "models": ["neural2", "wavenet", "studio"],
     "help": "Via Google Cloud API. 4M char free/bulan."},
]

IMAGE_PROVIDERS: List[Dict[str, Any]] = [
    {"key": "openai_image", "name": "OpenAI Images",
     "models": ["gpt-image-1", "dall-e-3"],
     "help": "Pakai OpenAI API key yang sama."},
    {"key": "flux", "name": "Flux (Black Forest Labs)",
     "models": ["flux-pro-1.1", "flux-dev", "flux-schnell"],
     "help": "Fotografis. Via Replicate atau bfl.ai."},
    {"key": "stability", "name": "Stability AI",
     "models": ["sd-3.5-large", "sd-3.5-medium", "sdxl"],
     "help": "platform.stability.ai."},
    {"key": "ideogram", "name": "Ideogram",
     "models": ["ideogram-v2", "ideogram-v2-turbo"],
     "help": "Juara text-in-image. ideogram.ai."},
    {"key": "recraft", "name": "Recraft",
     "models": ["recraft-v3"], "help": "Vector + brand-consistent. recraft.ai."},
    {"key": "midjourney", "name": "Midjourney (proxy)", "badge": {"label": "BETA", "kind": "beta"},
     "models": ["v6.1", "v6", "niji-6"],
     "help": "Belum ada API resmi — butuh proxy pihak ketiga."},
]

STORAGE_PROVIDERS: List[Dict[str, Any]] = [
    {"key": "local", "name": "Local filesystem", "badge": {"label": "DEFAULT", "kind": "free"},
     "no_key": True, "help": "File di data/ folder project. Tidak butuh setup."},
    {"key": "supabase", "name": "Supabase Storage", "no_key": True,
     "fields": [
         {"name": "url", "label": "Project URL", "kind": "text"},
         {"name": "service_role", "label": "Service Role Key", "kind": "password"},
         {"name": "bucket", "label": "Bucket Name (public read)", "kind": "text"},
     ],
     "help": "Free tier 500MB. supabase.com."},
    {"key": "s3", "name": "AWS S3", "no_key": True,
     "fields": [
         {"name": "access_key", "label": "Access Key ID", "kind": "text"},
         {"name": "secret_key", "label": "Secret Access Key", "kind": "password"},
         {"name": "bucket", "label": "Bucket", "kind": "text"},
         {"name": "region", "label": "Region", "kind": "text"},
     ],
     "help": "Standar industri. IAM user dengan S3 permission."},
    {"key": "r2", "name": "Cloudflare R2", "no_key": True,
     "fields": [
         {"name": "account_id", "label": "Account ID", "kind": "text"},
         {"name": "access_key", "label": "Access Key ID", "kind": "text"},
         {"name": "secret_key", "label": "Secret", "kind": "password"},
         {"name": "bucket", "label": "Bucket", "kind": "text"},
     ],
     "help": "Egress gratis. dash.cloudflare.com → R2."},
    {"key": "gcs", "name": "Google Cloud Storage", "no_key": True,
     "fields": [
         {"name": "service_account_json", "label": "Service Account JSON", "kind": "textarea"},
         {"name": "bucket", "label": "Bucket", "kind": "text"},
     ],
     "help": "Enterprise. Butuh service account key."},
]

PROVIDER_SECTIONS = [
    ("llm",     "LLM Providers",     "Untuk nulis script, hook, CTA, dan ngerakit prompt video.", LLM_PROVIDERS),
    ("video",   "Video Generation",  "Model yang beneran ngegenerate video UGC-nya.",             VIDEO_PROVIDERS),
    ("voice",   "Voice / TTS",       "Text-to-speech buat voice-over creator (opsional).",         VOICE_PROVIDERS),
    ("image",   "Image Generation",  "Buat product shot, creator avatar, atau thumbnail.",         IMAGE_PROVIDERS),
    ("storage", "Storage Backend",   "Tempat nyimpen asset biar bisa di-reference URL publik.",    STORAGE_PROVIDERS),
]


def all_setting_keys() -> set:
    """Every key the settings page may read/write."""
    keys = {
        "VIDEO_PROVIDER", "VOICE_PROVIDER", "LLM_PROVIDER", "IMAGE_PROVIDER", "STORAGE_PROVIDER",
        "DEFAULT_ASPECT", "DEFAULT_DURATION", "APP_ENV",
        # legacy / env-mirror keys kept for backwards compatibility
        "GEMINI_API_KEY", "GEMINI_MODEL",
        "NVIDIA_API_KEY", "NVIDIA_MODEL", "NVIDIA_BASE_URL",
    }
    for _, _, _, providers in PROVIDER_SECTIONS:
        for p in providers:
            prefix = p["key"].upper()
            if not p.get("no_key"):
                keys.add(f"{prefix}_API_KEY")
            if p.get("models"):
                keys.add(f"{prefix}_MODEL")
            for f in p.get("fields", []) or []:
                keys.add(f"{prefix}_{f['name'].upper()}")
    return keys


SETTING_KEYS = all_setting_keys()


def get_config(db: Session, key: str, default: str = "") -> str:
    row = db.query(Setting).filter(Setting.key == key).one_or_none()
    if row and row.value:
        return row.value
    return os.getenv(key, default)


def set_config(db: Session, key: str, value: str) -> None:
    row = db.query(Setting).filter(Setting.key == key).one_or_none()
    if row is None:
        row = Setting(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    db.commit()


def delete_config(db: Session, key: str) -> None:
    row = db.query(Setting).filter(Setting.key == key).one_or_none()
    if row is not None:
        db.delete(row)
        db.commit()


def mask_secret(value: Optional[str]) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "•" * len(value)
    return "••••••••••" + value[-4:]


def is_set(db: Session, key: str) -> bool:
    """True if a setting has a non-empty value (DB or env)."""
    return bool(get_config(db, key))


def provider_status(db: Session, provider: Dict[str, Any]) -> Dict[str, Any]:
    """Compute UI status for one provider."""
    prefix = provider["key"].upper()
    api_key = get_config(db, f"{prefix}_API_KEY") if not provider.get("no_key") else ""
    model = get_config(db, f"{prefix}_MODEL", "")
    field_values = {}
    for f in provider.get("fields", []) or []:
        field_values[f["name"]] = get_config(db, f"{prefix}_{f['name'].upper()}", "")

    if provider.get("no_key"):
        # Storage providers: considered "configured" when at least one required field is set
        configured = any(field_values.values()) or provider["key"] == "local"
    else:
        configured = bool(api_key)

    return {
        "configured": configured,
        "api_key_mask": mask_secret(api_key),
        "model": model,
        "field_values": field_values,
    }
