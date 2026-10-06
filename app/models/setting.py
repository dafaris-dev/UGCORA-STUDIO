from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.models.database import Base


class Setting(Base):
    """Key/value overrides for runtime-configurable settings."""
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(120), unique=True, nullable=False, index=True)
    value = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
