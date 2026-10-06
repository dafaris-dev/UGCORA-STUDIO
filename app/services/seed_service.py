"""Seed demo creators (fictional)."""
import logging
from sqlalchemy.orm import Session
from app.models.creator import Creator

logger = logging.getLogger(__name__)

DEMO_CREATORS = [
    {"name": "Emma Rivers", "gender": "Female", "category": "Lifestyle",
     "style": "Casual, Everyday", "personality": "Friendly, warm, chatty",
     "age_appearance": "22-26", "default_voice": "Female - Casual Friendly",
     "description": "Energetic lifestyle creator who talks like your best friend."},
    {"name": "Sofia Lane", "gender": "Female", "category": "Beauty",
     "style": "Soft Glam", "personality": "Confident, soothing, aspirational",
     "age_appearance": "24-28", "default_voice": "Female - Luxury Calm",
     "description": "Beauty creator focused on honest reviews."},
    {"name": "Mia Chen", "gender": "Female", "category": "Fitness",
     "style": "Athletic", "personality": "Upbeat, motivating",
     "age_appearance": "23-27", "default_voice": "Female - Energetic",
     "description": "Fitness creator for daily routines."},
    {"name": "Noah Carter", "gender": "Male", "category": "Technology",
     "style": "Casual Tech", "personality": "Smart, grounded, curious",
     "age_appearance": "25-30", "default_voice": "Male - Friendly Professional",
     "description": "Tech reviewer with a human touch."},
    {"name": "Liam Hart", "gender": "Male", "category": "Fashion",
     "style": "Streetwear", "personality": "Cool, understated",
     "age_appearance": "22-26", "default_voice": "Male - Casual",
     "description": "Fashion creator showing fits and finds."},
    {"name": "Ava Monroe", "gender": "Female", "category": "Professional",
     "style": "Business Casual", "personality": "Clear, confident, authoritative",
     "age_appearance": "28-34", "default_voice": "Female - Professional",
     "description": "Explains products with clarity for professionals."},
    {"name": "Ethan Rowe", "gender": "Male", "category": "Business",
     "style": "Suited Casual", "personality": "Articulate, persuasive",
     "age_appearance": "30-36", "default_voice": "Male - Luxury",
     "description": "Premium business content creator."},
    {"name": "Zoe Palmer", "gender": "Female", "category": "Lifestyle",
     "style": "Minimalist", "personality": "Calm, thoughtful",
     "age_appearance": "26-30", "default_voice": "Female - Calm",
     "description": "Soft-spoken minimalist lifestyle creator."},
]


def seed_creators(db: Session) -> None:
    if db.query(Creator).count() > 0:
        return
    for data in DEMO_CREATORS:
        db.add(Creator(language="English", is_demo=True, **data))
    db.commit()
    logger.info("Seeded %s demo creators.", len(DEMO_CREATORS))
