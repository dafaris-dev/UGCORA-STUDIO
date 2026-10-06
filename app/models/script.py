from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from app.models.database import Base


class Script(Base):
    __tablename__ = "scripts"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)
    template = Column(String(80), default="Problem → Solution")
    duration_seconds = Column(Integer, default=30)
    tone = Column(String(80), default="Casual")
    hook = Column(Text, default="")
    body = Column(Text, default="")
    cta = Column(Text, default="")
    full_text = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
