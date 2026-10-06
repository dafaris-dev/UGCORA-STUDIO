from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.models.database import Base


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    benefits = Column(Text, default="")
    target_audience = Column(Text, default="")
    website = Column(String(500), default="")
    cta = Column(String(300), default="")
    image_path = Column(String(500), default="")
    video_path = Column(String(500), default="")
    logo_path = Column(String(500), default="")

    # Gemini analysis fields (editable after)
    category = Column(String(200), default="")
    analyzed_audience = Column(Text, default="")
    customer_problem = Column(Text, default="")
    main_benefits = Column(Text, default="")
    usp = Column(Text, default="")
    marketing_angle = Column(Text, default="")
    ugc_hook = Column(Text, default="")
    recommended_cta = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
