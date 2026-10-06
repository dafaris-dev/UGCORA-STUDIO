from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from app.models.database import Base


class Generation(Base):
    """Single unified record for an avatar/video generation run.

    One row covers: the product, the avatar spec, the structured prompt,
    the provider/model used, status, outputs, and totals for token tracking.
    """
    __tablename__ = "generations"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)
    title = Column(String(200), default="UGC Avatar")

    # ─── Avatar spec (Subject · Hair & Face · Pose · Outfit · Setting) ───
    gender          = Column(String(40), default="")
    age_range       = Column(String(40), default="")
    ethnicity       = Column(String(80), default="")
    skin_tone       = Column(String(40), default="")

    hijab           = Column(String(60), default="")
    hair_style      = Column(String(80), default="")
    hair_color      = Column(String(40), default="")
    grooming        = Column(String(80), default="")
    expression      = Column(String(60), default="")
    glasses         = Column(String(60), default="")

    body_pose       = Column(String(60), default="")
    framing         = Column(String(80), default="")
    hand_gesture    = Column(String(80), default="")

    outfit          = Column(String(120), default="")
    outfit_color    = Column(String(60), default="")

    setting         = Column(String(80), default="")
    lighting        = Column(String(80), default="")
    style           = Column(String(80), default="")
    aspect_ratio    = Column(String(10), default="9:16")
    resolution      = Column(String(20), default="1080p")
    extras          = Column(Text, default="")
    languages       = Column(Text, default="")  # comma-separated list of selected languages

    # ─── Script (optional) ───
    script_text     = Column(Text, default="")
    script_tone     = Column(String(40), default="")
    script_duration = Column(Integer, default=0)

    # ─── Prompt + providers ───
    prompt          = Column(Text, default="")
    negative_prompt = Column(Text, default="")
    llm_provider    = Column(String(60), default="")
    llm_model       = Column(String(120), default="")
    video_provider  = Column(String(60), default="")
    video_model     = Column(String(120), default="")
    generation_id   = Column(String(200), default="")

    # ─── Status / outputs ───
    status          = Column(String(40), default="draft")  # draft, generating_prompt, prompt_ready, generating_video, completed, failed
    progress        = Column(Integer, default=0)
    error_message   = Column(Text, default="")
    image_path      = Column(String(500), default="")   # avatar image (if image-only run)
    video_path      = Column(String(500), default="")
    thumbnail_path  = Column(String(500), default="")

    # ─── Token totals (sum of all token_usage rows for this gen) ───
    prompt_tokens   = Column(Integer, default=0)
    output_tokens   = Column(Integer, default=0)
    total_tokens    = Column(Integer, default=0)

    created_at      = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at    = Column(DateTime, nullable=True)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Backwards-compat alias for older imports
VideoGeneration = Generation
