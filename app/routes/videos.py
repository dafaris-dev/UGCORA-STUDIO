"""Core routes for Create Video / Project / Generation detail / Avatar prompt + generate."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
import httpx

from app.models.database import get_db
from app.models.product import Product
from app.models.video import Generation
from app.deps import require_login, require_login_api
from app.services.config_service import get_config, LLM_PROVIDERS, VIDEO_PROVIDERS
from app.services.file_service import save_upload, delete_file, save_bytes, ALLOWED_IMAGE_EXT, ALLOWED_VIDEO_EXT
from app.services.gemini_service import _call_raw as gemini_call, GeminiError
from app.services.groq_service import _call as groq_call, GroqError
from app.services.prompt_service import build_local_prompt, build_ai_prompt
from app.services.video_service import enqueue_generation
from app.services import token_tracker

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


# ─────────── Form options (shown in the dropdowns) ───────────
FORM_OPTIONS = {
    "gender":       ["Perempuan", "Laki-laki", "Non-binary"],
    "age_range":    ["18-24", "25-30", "30-35", "35-40", "40-50", "50+"],
    "ethnicity":    ["Southeast Asian", "East Asian", "South Asian", "Middle Eastern",
                     "African", "European / Western", "Latin American", "Mixed"],
    "skin_tone":    ["Auto", "Fair", "Light", "Medium", "Tan", "Deep", "Dark"],
    "hijab":        ["Tanpa hijab", "Hijab segi empat", "Hijab pashmina", "Hijab instant", "Khimar"],
    "hair_style":   ["Sebahu", "Panjang lurus", "Panjang keriting", "Bob pendek", "Pixie cut",
                     "Ponytail", "Bun", "Pendek rapi (pria)", "Undercut"],
    "hair_color":   ["Hitam", "Coklat gelap", "Coklat", "Pirang", "Highlight", "Ombre", "Dyed vibrant"],
    "grooming":     ["Natural / no makeup", "Light makeup / dewy", "Full glam", "Beard natural (pria)",
                     "Clean shaven (pria)"],
    "expression":   ["Senyum ramah", "Senyum lebar", "Serius", "Terkejut", "Thinking", "Confident"],
    "glasses":      ["Tanpa kacamata", "Kacamata minus bulat", "Kacamata minus kotak", "Sunglasses"],
    "body_pose":    ["Duduk", "Berdiri", "Jongkok", "Bersandar"],
    "framing":      ["Chest-up (talking head)", "Close-up wajah", "Medium shot", "Full body",
                     "Over-the-shoulder"],
    "hand_gesture": ["Gestur natural", "Memegang produk", "Pointing ke kamera", "Thumbs up",
                     "Explaining with hands"],
    "outfit":       ["Kaos polos", "Kemeja", "Hoodie", "Jaket denim", "Dress casual",
                     "Blazer formal", "Sport outfit", "Streetwear"],
    "outfit_color": ["Auto", "Putih", "Hitam", "Krem / Beige", "Abu-abu", "Pastel", "Earth tone",
                     "Vibrant warna cerah"],
    "setting":      ["Ruang tamu", "Kamar tidur", "Dapur", "Kamar mandi", "Office", "Cafe",
                     "Gym", "Toko / Store", "Outdoor jalan", "Taman / Nature", "Studio minimalis"],
    "lighting":     ["Natural window light", "Golden hour", "Soft diffused", "Studio key",
                     "Overhead ring light", "Ambient warm", "Night neon"],
    "style":        ["Photorealistic UGC", "Cinematic", "Fashion editorial", "Lifestyle magazine",
                     "Candid snapshot"],
    "aspect_ratio": ["9:16 (Reels / UGC)", "1:1 (Square)", "16:9 (Landscape)"],
}


# ─────────── Pages ───────────

@router.get("/create", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def create_page(request: Request, db: Session = Depends(get_db),
                       product_id: Optional[int] = None):
    products = db.query(Product).order_by(desc(Product.updated_at)).all()
    product = db.get(Product, product_id) if product_id else None

    # Provider readiness
    gemini_ready = bool(get_config(db, "GEMINI_API_KEY"))
    groq_ready = bool(get_config(db, "GROQ_API_KEY"))
    any_llm_ready = gemini_ready or groq_ready
    video_provider = get_config(db, "VIDEO_PROVIDER", "")
    video_ready = bool(video_provider and get_config(db, f"{video_provider.upper()}_API_KEY"))

    return templates.TemplateResponse(request, "create_video.html", {
        "request": request,
        "options": FORM_OPTIONS,
        "products": products,
        "selected_product": product,
        "gemini_ready": gemini_ready,
        "groq_ready": groq_ready,
        "any_llm_ready": any_llm_ready,
        "video_ready": video_ready,
        "video_provider": video_provider,
    })


@router.get("/project", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def project_page(request: Request, db: Session = Depends(get_db)):
    gens = db.query(Generation).order_by(desc(Generation.created_at)).all()
    return templates.TemplateResponse(request, "project.html",
                                      {"request": request, "gens": gens})


@router.get("/project/{gen_id}", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def generation_detail(gen_id: int, request: Request, db: Session = Depends(get_db)):
    gen = db.get(Generation, gen_id)
    if not gen:
        raise HTTPException(404, "Generation not found")
    product = db.get(Product, gen.product_id) if gen.product_id else None
    return templates.TemplateResponse(request, "generation.html", {
        "request": request, "gen": gen, "product": product,
    })


# ─────────── Product upload ───────────

@router.post("/api/products", dependencies=[Depends(require_login_api)])
async def api_create_product(
    name: str = Form(...),
    description: str = Form(""),
    benefits: str = Form(""),
    cta: str = Form(""),
    website: str = Form(""),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    p = Product(name=name.strip(), description=description.strip(),
                 benefits=benefits.strip(), cta=cta.strip(), website=website.strip())
    try:
        if image and image.filename:
            p.image_path = save_upload(image, "products", ALLOWED_IMAGE_EXT)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    db.add(p); db.commit(); db.refresh(p)
    return {"id": p.id, "name": p.name, "image_path": p.image_path}


@router.get("/api/products", dependencies=[Depends(require_login_api)])
async def api_list_products(db: Session = Depends(get_db)):
    products = db.query(Product).order_by(desc(Product.updated_at)).all()
    return [{"id": p.id, "name": p.name, "description": p.description,
             "image_path": p.image_path} for p in products]


@router.delete("/api/products/{pid}", dependencies=[Depends(require_login_api)])
async def api_delete_product(pid: int, db: Session = Depends(get_db)):
    p = db.get(Product, pid)
    if not p: raise HTTPException(404, "Product not found")
    delete_file(p.image_path)
    db.delete(p); db.commit()
    return {"ok": True}


# ─────────── Prompt generation ───────────

class PromptRequest(BaseModel):
    product_id: Optional[int] = None
    spec: dict
    use_ai: bool = True


def _llm_caller(db: Session):
    """Pick an available free LLM and return (name, model, caller(prompt)->dict)."""
    gkey = get_config(db, "GEMINI_API_KEY")
    gmodel = get_config(db, "GEMINI_MODEL", "gemini-2.0-flash")
    if gkey:
        def call(p: str):
            return gemini_call(gkey, gmodel, p, temperature=0.6)
        return "gemini", gmodel, call

    qkey = get_config(db, "GROQ_API_KEY")
    qmodel = get_config(db, "GROQ_MODEL", "llama-3.3-70b-versatile")
    if qkey:
        def call(p: str):
            return groq_call(qkey, qmodel, p, temperature=0.6)
        return "groq", qmodel, call

    # Fallback: any configured LLM provider using OpenAI-compatible chat API?
    # For MVP we require Gemini or Groq for prompt building.
    return None, None, None


@router.post("/api/prompt/build", dependencies=[Depends(require_login_api)])
async def api_build_prompt(req: PromptRequest, db: Session = Depends(get_db)):
    product = db.get(Product, req.product_id) if req.product_id else None
    product_dict = {"name": product.name, "description": product.description} if product else None

    if not req.use_ai:
        text = build_local_prompt(req.spec, product_dict)
        return {"prompt": text, "source": "local", "tokens": {"total_tokens": 0}}

    name, model, call = _llm_caller(db)
    if call is None:
        text = build_local_prompt(req.spec, product_dict)
        return {"prompt": text, "source": "local_fallback",
                "tokens": {"total_tokens": 0},
                "warning": "Gemini/Groq belum diisi — pakai prompt lokal (tanpa translate AI)."}

    try:
        prompt_text, tokens = build_ai_prompt(call, req.spec, product_dict)
    except (GeminiError, GroqError) as exc:
        logger.warning("AI prompt build failed, falling back: %s", exc)
        text = build_local_prompt(req.spec, product_dict)
        return {"prompt": text, "source": "local_fallback",
                "tokens": {"total_tokens": 0}, "warning": str(exc)}

    token_tracker.record(db, agent="prompt-build", provider=name, model=model,
                          input_tokens=tokens.get("input_tokens", 0),
                          output_tokens=tokens.get("output_tokens", 0),
                          total_tokens=tokens.get("total_tokens", 0),
                          product_id=req.product_id)
    return {"prompt": prompt_text, "source": name, "model": model, "tokens": tokens}


# ─────────── Create generation ───────────

class GenerateRequest(BaseModel):
    product_id: Optional[int] = None
    title: Optional[str] = ""
    spec: dict
    prompt: str
    negative_prompt: str = ""


@router.post("/api/generations", dependencies=[Depends(require_login_api)])
async def api_create_generation(req: GenerateRequest, db: Session = Depends(get_db)):
    if not req.prompt.strip():
        raise HTTPException(400, "Prompt is required.")

    product = db.get(Product, req.product_id) if req.product_id else None
    video_provider = get_config(db, "VIDEO_PROVIDER", "nvidia")
    video_model = get_config(db, f"{video_provider.upper()}_MODEL", "") if video_provider else ""

    spec = req.spec or {}
    aspect = (spec.get("aspect_ratio") or "9:16").split()[0]  # strip "(Reels / UGC)" suffix

    gen = Generation(
        product_id=req.product_id,
        title=req.title or (f"{product.name} · UGC" if product else "UGC Avatar"),
        gender=spec.get("gender", ""), age_range=spec.get("age_range", ""),
        ethnicity=spec.get("ethnicity", ""), skin_tone=spec.get("skin_tone", ""),
        hijab=spec.get("hijab", ""), hair_style=spec.get("hair_style", ""),
        hair_color=spec.get("hair_color", ""), grooming=spec.get("grooming", ""),
        expression=spec.get("expression", ""), glasses=spec.get("glasses", ""),
        body_pose=spec.get("body_pose", ""), framing=spec.get("framing", ""),
        hand_gesture=spec.get("hand_gesture", ""),
        outfit=spec.get("outfit", ""), outfit_color=spec.get("outfit_color", ""),
        setting=spec.get("setting", ""), lighting=spec.get("lighting", ""),
        style=spec.get("style", ""), aspect_ratio=aspect,
        extras=spec.get("extras", ""),
        prompt=req.prompt, negative_prompt=req.negative_prompt,
        video_provider=video_provider, video_model=video_model,
        status="queued", progress=0,
    )
    db.add(gen); db.commit(); db.refresh(gen)

    enqueue_generation(gen.id)
    return {"id": gen.id, "status": gen.status}


@router.get("/api/generations/{gen_id}/status", dependencies=[Depends(require_login_api)])
async def api_gen_status(gen_id: int, db: Session = Depends(get_db)):
    g = db.get(Generation, gen_id)
    if not g: raise HTTPException(404, "Generation not found")
    return {
        "id": g.id, "status": g.status, "progress": g.progress,
        "error_message": g.error_message, "video_path": g.video_path,
        "image_path": g.image_path, "total_tokens": g.total_tokens,
    }


@router.delete("/api/generations/{gen_id}", dependencies=[Depends(require_login_api)])
async def api_gen_delete(gen_id: int, db: Session = Depends(get_db)):
    g = db.get(Generation, gen_id)
    if not g: raise HTTPException(404, "Generation not found")
    for p in (g.video_path, g.image_path, g.thumbnail_path):
        if p and p.startswith("data/"):
            delete_file(p)
    db.delete(g); db.commit()
    return {"ok": True}


@router.get("/api/generations/{gen_id}/download")
async def api_gen_download(gen_id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        raise HTTPException(401, "Not authenticated")
    g = db.get(Generation, gen_id)
    if not g or not g.video_path:
        raise HTTPException(404, "No file available")

    path = g.video_path
    if path.startswith("http://") or path.startswith("https://"):
        try:
            with httpx.Client(timeout=120.0) as c:
                r = c.get(path)
                if r.status_code != 200:
                    raise HTTPException(502, f"Remote download failed: {r.status_code}")
                local = save_bytes(r.content, "videos", ".mp4")
                g.video_path = local
                db.commit()
                path = local
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"Remote download failed: {exc}")

    p = Path(path)
    if not p.exists():
        raise HTTPException(404, "File missing on disk.")
    return FileResponse(str(p), filename=f"ugcora-{gen_id}.mp4", media_type="video/mp4")
