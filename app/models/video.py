from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from app.models.database import Base


class VideoGeneration(Base):
    __tablename__ = "video_generations"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)
    script_id = Column(Integer, ForeignKey("scripts.id"), nullable=True)

    title = Column(String(200), default="UGC Video")
    provider = Column(String(60), default="nvidia")
    model = Column(String(120), default="")
    generation_id = Column(String(200), default="")

    status = Column(String(40), default="pending")  # pending, preparing, submitting, generating, rendering, completed, failed
    progress = Column(Integer, default=0)
    error_message = Column(Text, default="")

    prompt = Column(Text, default="")
    negative_prompt = Column(Text, default="")
    aspect_ratio = Column(String(10), default="9:16")
    resolution = Column(String(20), default="1080p")
    duration_seconds = Column(Integer, default=30)

    location = Column(String(100), default="")
    camera = Column(String(100), default="")
    lighting = Column(String(100), default="")
    voice_name = Column(String(120), default="")
    voice_style = Column(String(120), default="")

    video_path = Column(String(500), default="")
    thumbnail_path = Column(String(500), default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
