from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime
from app.models.database import Base


class Creator(Base):
    __tablename__ = "creators"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    category = Column(String(80), default="Lifestyle")
    gender = Column(String(40), default="Female")
    style = Column(String(200), default="")
    personality = Column(String(300), default="")
    age_appearance = Column(String(80), default="")
    language = Column(String(80), default="English")
    default_voice = Column(String(120), default="")
    description = Column(Text, default="")
    image_path = Column(String(500), default="")
    favorite = Column(Boolean, default=False)
    is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
