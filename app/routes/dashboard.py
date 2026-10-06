from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database import get_db
from app.models.product import Product
from app.models.video import Generation
from app.deps import require_login
from app.services.config_service import get_config
from app.services import token_tracker

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def dashboard(request: Request, db: Session = Depends(get_db)):
    gens = db.query(Generation).order_by(desc(Generation.created_at)).limit(6).all()
    product_count = db.query(Product).count()
    gen_count = db.query(Generation).count()
    token_summary = token_tracker.summary(db, days=30)

    gemini_ready = bool(get_config(db, "GEMINI_API_KEY"))
    groq_ready = bool(get_config(db, "GROQ_API_KEY"))
    video_provider = get_config(db, "VIDEO_PROVIDER", "")
    video_ready = bool(video_provider and get_config(db, f"{video_provider.upper()}_API_KEY"))

    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request,
        "gens": gens,
        "product_count": product_count,
        "gen_count": gen_count,
        "tokens_30d": token_summary["total_tokens"],
        "runs_30d": token_summary["runs"],
        "gemini_ready": gemini_ready,
        "groq_ready": groq_ready,
        "video_ready": video_ready,
        "video_provider": video_provider,
    })
