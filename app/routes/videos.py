from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pathlib import Path
import httpx
import logging

from app.models.database import get_db
from app.models.product import Product
from app.models.creator import Creator
from app.models.script import Script
from app.models.project import Project
from app.models.video import VideoGeneration
from app.deps import require_login, require_login_api
from app.services.config_service import get_config
from app.services.prompt_service import build_prompt
from app.services.gemini_service import generate_video_prompt, GeminiError
from app.services.video_service import enqueue_generation
from app.services.file_service import save_bytes, delete_file

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


LOCATIONS = ["Bedroom", "Living Room", "Kitchen", "Office", "Cafe",
             "Gym", "Bathroom", "Store", "Outdoor", "Studio"]
CAMERAS = ["Phone selfie", "Handheld", "Tripod", "Talking head",
           "Close-up", "Product demonstration"]
LIGHTING_OPTIONS = ["Natural window", "Soft diffused", "Golden hour", "Studio key",
                    "Overhead ring", "Ambient warm"]
ASPECT_RATIOS = ["9:16", "1:1", "16:9"]
RESOLUTIONS = ["720p", "1080p"]


@router.get("/videos", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def videos_page(request: Request, db: Session = Depends(get_db)):
    videos = db.query(VideoGeneration).order_by(desc(VideoGeneration.created_at)).all()
    return templates.TemplateResponse(request, "videos.html", {"request": request, "videos": videos})


@router.get("/create", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def create_video_page(request: Request, db: Session = Depends(get_db)):
    products = db.query(Product).order_by(desc(Product.updated_at)).all()
    creators = db.query(Creator).order_by(desc(Creator.favorite), Creator.name).all()
    gemini_ready = bool(get_config(db, "GEMINI_API_KEY"))
    nvidia_ready = bool(get_config(db, "NVIDIA_API_KEY") and get_config(db, "NVIDIA_MODEL"))
    return templates.TemplateResponse(request, "create_video.html", {
        "request": request,
        "products": products,
        "creators": creators,
        "locations": LOCATIONS,
        "cameras": CAMERAS,
        "lighting_options": LIGHTING_OPTIONS,
        "aspect_ratios": ASPECT_RATIOS,
        "resolutions": RESOLUTIONS,
        "gemini_ready": gemini_ready,
        "nvidia_ready": nvidia_ready,
    })


@router.get("/videos/{video_id}", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def video_detail(video_id: int, request: Request, db: Session = Depends(get_db)):
    video = db.get(VideoGeneration, video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    product = db.get(Product, video.product_id) if video.product_id else None
    creator = db.get(Creator, video.creator_id) if video.creator_id else None
    script = db.get(Script, video.script_id) if video.script_id else None
    return templates.TemplateResponse(request, "video_detail.html", {
        "request": request, "video": video, "product": product,
        "creator": creator, "script": script,
    })


# ---------- API ----------

class VideoPromptRequest(BaseModel):
    product_id: int
    creator_id: Optional[int] = None
    script_id: Optional[int] = None
    location: str = ""
    camera: str = ""
    lighting: str = ""
    action: str = ""
    clothing: str = ""
    voice: str = ""
    aspect_ratio: str = "9:16"
    resolution: str = "1080p"
    duration_seconds: int = 30
    use_gemini: bool = True


@router.post("/api/videos/prompt", dependencies=[Depends(require_login_api)])
async def api_build_prompt(req: VideoPromptRequest, db: Session = Depends(get_db)):
    product = db.get(Product, req.product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    creator = db.get(Creator, req.creator_id) if req.creator_id else None
    script = db.get(Script, req.script_id) if req.script_id else None

    ctx = {
        "product_name": product.name,
        "product_description": product.description,
        "product_benefits": product.main_benefits or product.benefits,
        "creator_name": creator.name if creator else "",
        "creator_personality": creator.personality if creator else "",
        "creator_age": creator.age_appearance if creator else "",
        "clothing": req.clothing,
        "location": req.location,
        "camera": req.camera,
        "lighting": req.lighting,
        "action": req.action,
        "script": script.full_text if script else "",
        "voice": req.voice,
        "marketing_angle": product.marketing_angle,
        "aspect_ratio": req.aspect_ratio,
        "resolution": req.resolution,
        "duration_seconds": req.duration_seconds,
        "cta": product.recommended_cta or product.cta,
    }

    prompt_text = ""
    if req.use_gemini:
        api_key = get_config(db, "GEMINI_API_KEY")
        model = get_config(db, "GEMINI_MODEL", "gemini-2.0-flash")
        if api_key:
            try:
                prompt_text = generate_video_prompt(api_key, model, ctx)
            except GeminiError as exc:
                logger.warning("Gemini prompt build failed, falling back: %s", exc)

    if not prompt_text:
        prompt_text = build_prompt(ctx)

    return {"prompt": prompt_text}


class VideoGenerateRequest(BaseModel):
    product_id: int
    creator_id: Optional[int] = None
    script_id: Optional[int] = None
    project_id: Optional[int] = None
    title: str = "UGC Video"
    prompt: str
    negative_prompt: str = ""
    aspect_ratio: str = "9:16"
    resolution: str = "1080p"
    duration_seconds: int = 30
    location: str = ""
    camera: str = ""
    lighting: str = ""
    voice_name: str = ""
    voice_style: str = ""


@router.post("/api/videos/generate", dependencies=[Depends(require_login_api)])
async def api_generate_video(req: VideoGenerateRequest, db: Session = Depends(get_db)):
    product = db.get(Product, req.product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    if req.creator_id and not db.get(Creator, req.creator_id):
        raise HTTPException(404, "Creator not found")
    if req.script_id and not db.get(Script, req.script_id):
        raise HTTPException(404, "Script not found")
    if req.project_id and not db.get(Project, req.project_id):
        raise HTTPException(404, "Project not found")
    if not req.prompt.strip():
        raise HTTPException(400, "Prompt is required.")

    provider_name = get_config(db, "VIDEO_PROVIDER", "nvidia")
    model = get_config(db, "NVIDIA_MODEL", "") if provider_name == "nvidia" else ""

    video = VideoGeneration(
        project_id=req.project_id, product_id=req.product_id,
        creator_id=req.creator_id, script_id=req.script_id,
        title=req.title or "UGC Video",
        provider=provider_name, model=model,
        status="pending", progress=0,
        prompt=req.prompt, negative_prompt=req.negative_prompt,
        aspect_ratio=req.aspect_ratio, resolution=req.resolution,
        duration_seconds=req.duration_seconds,
        location=req.location, camera=req.camera, lighting=req.lighting,
        voice_name=req.voice_name, voice_style=req.voice_style,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    enqueue_generation(video.id)
    return {"id": video.id, "status": video.status}


@router.get("/api/videos/{video_id}/status", dependencies=[Depends(require_login_api)])
async def api_video_status(video_id: int, db: Session = Depends(get_db)):
    v = db.get(VideoGeneration, video_id)
    if not v:
        raise HTTPException(404, "Video not found")
    return {
        "id": v.id, "status": v.status, "progress": v.progress,
        "error_message": v.error_message, "video_path": v.video_path,
        "provider": v.provider, "model": v.model, "generation_id": v.generation_id,
    }


@router.get("/api/videos/{video_id}", dependencies=[Depends(require_login_api)])
async def api_video_get(video_id: int, db: Session = Depends(get_db)):
    v = db.get(VideoGeneration, video_id)
    if not v:
        raise HTTPException(404, "Video not found")
    return {c.name: getattr(v, c.name) for c in v.__table__.columns}


@router.delete("/api/videos/{video_id}", dependencies=[Depends(require_login_api)])
async def api_video_delete(video_id: int, db: Session = Depends(get_db)):
    v = db.get(VideoGeneration, video_id)
    if not v:
        raise HTTPException(404, "Video not found")
    if v.video_path and v.video_path.startswith("data/"):
        delete_file(v.video_path)
    db.delete(v)
    db.commit()
    return {"ok": True}


@router.post("/api/videos/{video_id}/variation", dependencies=[Depends(require_login_api)])
async def api_video_variation(video_id: int, db: Session = Depends(get_db)):
    v = db.get(VideoGeneration, video_id)
    if not v:
        raise HTTPException(404, "Video not found")
    clone = VideoGeneration(
        project_id=v.project_id, product_id=v.product_id,
        creator_id=v.creator_id, script_id=v.script_id,
        title=f"{v.title} (variation)",
        provider=v.provider, model=v.model, status="pending", progress=0,
        prompt=v.prompt, negative_prompt=v.negative_prompt,
        aspect_ratio=v.aspect_ratio, resolution=v.resolution,
        duration_seconds=v.duration_seconds,
        location=v.location, camera=v.camera, lighting=v.lighting,
        voice_name=v.voice_name, voice_style=v.voice_style,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    enqueue_generation(clone.id)
    return {"id": clone.id}


@router.get("/api/videos/{video_id}/download")
async def api_video_download(video_id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        raise HTTPException(401, "Not authenticated")
    v = db.get(VideoGeneration, video_id)
    if not v or not v.video_path:
        raise HTTPException(404, "Video not available")

    path = v.video_path
    if path.startswith("http://") or path.startswith("https://"):
        # Download remote to a local file so we can serve it back.
        try:
            with httpx.Client(timeout=120.0) as c:
                resp = c.get(path)
                if resp.status_code != 200:
                    raise HTTPException(502, f"Remote download failed: {resp.status_code}")
                local = save_bytes(resp.content, "videos", ".mp4")
                v.video_path = local
                db.commit()
                path = local
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"Remote download failed: {exc}")

    p = Path(path)
    if not p.exists():
        raise HTTPException(404, "Video file missing on disk.")
    return FileResponse(str(p), filename=f"ugcora-{video_id}.mp4", media_type="video/mp4")
