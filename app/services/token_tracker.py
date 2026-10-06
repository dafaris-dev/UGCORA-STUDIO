"""Record token usage per LLM call so the Biaya page can summarize it."""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.token_usage import TokenUsage
from app.models.video import Generation
from app.models.product import Product

logger = logging.getLogger(__name__)

FREE_PROVIDERS = {"gemini", "groq"}


def record(db: Session, *, agent: str, provider: str, model: str,
           input_tokens: int = 0, output_tokens: int = 0,
           total_tokens: Optional[int] = None,
           generation_id: Optional[int] = None,
           product_id: Optional[int] = None) -> TokenUsage:
    """Record one API call's usage, update the Generation total if linked."""
    if total_tokens is None:
        total_tokens = (input_tokens or 0) + (output_tokens or 0)
    row = TokenUsage(
        generation_id=generation_id,
        product_id=product_id,
        agent=agent,
        provider=provider.lower() if provider else "",
        model=model or "",
        input_tokens=input_tokens or 0,
        output_tokens=output_tokens or 0,
        total_tokens=total_tokens or 0,
        is_free=1 if (provider or "").lower() in FREE_PROVIDERS else 0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    if generation_id:
        gen = db.get(Generation, generation_id)
        if gen is not None:
            gen.prompt_tokens = (gen.prompt_tokens or 0) + (input_tokens or 0)
            gen.output_tokens = (gen.output_tokens or 0) + (output_tokens or 0)
            gen.total_tokens = (gen.total_tokens or 0) + (total_tokens or 0)
            db.commit()
    return row


def summary(db: Session, days: int = 30) -> Dict[str, Any]:
    cutoff = datetime.utcnow() - timedelta(days=days)
    q = db.query(TokenUsage).filter(TokenUsage.created_at >= cutoff)

    rows = q.all()
    total = sum(r.total_tokens for r in rows)
    runs = len(rows)

    by_provider: Dict[str, int] = {}
    by_agent: Dict[str, int] = {}
    by_product: Dict[str, int] = {}

    for r in rows:
        by_provider[r.provider or "unknown"] = by_provider.get(r.provider or "unknown", 0) + r.total_tokens
        by_agent[r.agent or "unknown"] = by_agent.get(r.agent or "unknown", 0) + r.total_tokens
        if r.product_id:
            product = db.get(Product, r.product_id)
            name = product.name if product else f"#{r.product_id}"
            by_product[name] = by_product.get(name, 0) + r.total_tokens

    recent = db.query(TokenUsage).filter(TokenUsage.created_at >= cutoff) \
        .order_by(desc(TokenUsage.created_at)).limit(10).all()

    recent_rows: List[Dict[str, Any]] = []
    for r in recent:
        product_name = ""
        if r.product_id:
            p = db.get(Product, r.product_id)
            if p: product_name = p.name
        recent_rows.append({
            "when": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "agent": r.agent,
            "product": product_name,
            "provider": r.provider,
            "model": r.model,
            "input": r.input_tokens,
            "output": r.output_tokens,
            "total": r.total_tokens,
            "free": bool(r.is_free),
        })

    return {
        "days": days,
        "total_tokens": total,
        "runs": runs,
        "by_provider": sorted(by_provider.items(), key=lambda x: -x[1]),
        "by_agent": sorted(by_agent.items(), key=lambda x: -x[1]),
        "by_product": sorted(by_product.items(), key=lambda x: -x[1]),
        "recent": recent_rows,
    }
