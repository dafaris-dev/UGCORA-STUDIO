from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database import get_db
from app.models.project import Project
from app.models.product import Product
from app.models.creator import Creator
from app.models.video import VideoGeneration
from app.deps import require_login
from app.services.config_service import get_config

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def dashboard(request: Request, db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(desc(Project.updated_at)).limit(5).all()
    videos = db.query(VideoGeneration).order_by(desc(VideoGeneration.created_at)).limit(6).all()
    product_count = db.query(Product).count()
    creator_count = db.query(Creator).count()

    gemini_ready = bool(get_config(db, "GEMINI_API_KEY") and get_config(db, "GEMINI_MODEL"))
    nvidia_ready = bool(get_config(db, "NVIDIA_API_KEY") and get_config(db, "NVIDIA_MODEL"))

    return templates.TemplateResponse(request, "dashboard.html", {
            "request": request,
            "projects": projects,
            "videos": videos,
            "product_count": product_count,
            "creator_count": creator_count,
            "gemini_ready": gemini_ready,
            "nvidia_ready": nvidia_ready,
            "video_provider": get_config(db, "VIDEO_PROVIDER", "nvidia"),
        },
    )
