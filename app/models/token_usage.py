from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.models.database import Base


class TokenUsage(Base):
    """Per-call token tracking so the Biaya page can summarize usage."""
    __tablename__ = "token_usage"
    id = Column(Integer, primary_key=True)
    generation_id = Column(Integer, ForeignKey("generations.id"), nullable=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)
    agent = Column(String(60), default="")       # e.g. "prompt-build", "script", "analyze"
    provider = Column(String(60), default="")    # gemini, groq, anthropic, openai, nvidia, …
    model = Column(String(120), default="")
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    is_free = Column(Integer, default=0)         # 1 if provider is a free-tier engine
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
