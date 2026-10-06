from fastapi import APIRouter, Depends, HTTPException, Form, Body
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.product import Product
from app.models.creator import Creator
from app.models.script import Script
from app.deps import require_login_api
from app.services.config_service import get_config
from app.services.gemini_service import (
    generate_script, rewrite_script, generate_hooks, generate_cta, GeminiError
)

router = APIRouter()


SCRIPT_TEMPLATES = [
    "Problem → Solution", "Product Review", "Unboxing", "First Impression",
    "3 Reasons Why", "POV", "Storytelling", "Testimonial",
    "Product Demonstration", "Before & After", "Product Recommendation",
    "Limited Offer",
]
TONES = ["Casual", "Friendly", "Energetic", "Professional", "Luxury",
         "Funny", "Persuasive", "Authentic"]
DURATIONS = [15, 30, 45, 60]


class ScriptGenerateRequest(BaseModel):
    product_id: int
    creator_id: Optional[int] = None
    project_id: Optional[int] = None
    template: str = "Problem → Solution"
    duration_seconds: int = 30
    tone: str = "Casual"
    marketing_angle: str = ""


@router.get("/api/scripts/templates", dependencies=[Depends(require_login_api)])
async def api_templates():
    return {"templates": SCRIPT_TEMPLATES, "tones": TONES, "durations": DURATIONS}


@router.post("/api/scripts/generate", dependencies=[Depends(require_login_api)])
async def api_generate_script(payload: ScriptGenerateRequest, db: Session = Depends(get_db)):
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    creator = db.get(Creator, payload.creator_id) if payload.creator_id else None

    api_key = get_config(db, "GEMINI_API_KEY")
    model = get_config(db, "GEMINI_MODEL", "gemini-2.0-flash")
    if not api_key:
        raise HTTPException(400, "Gemini API key is not configured.")

    ctx = {
        "product_name": product.name,
        "product_benefits": product.main_benefits or product.benefits,
        "target_audience": product.analyzed_audience or product.target_audience,
        "creator_name": creator.name if creator else "",
        "creator_personality": creator.personality if creator else "",
        "marketing_angle": payload.marketing_angle or product.marketing_angle,
        "template": payload.template,
        "tone": payload.tone,
        "duration_seconds": payload.duration_seconds,
        "cta": product.recommended_cta or product.cta,
    }
    try:
        data = generate_script(api_key, model, ctx)
    except GeminiError as exc:
        raise HTTPException(502, f"Gemini request failed: {exc}")

    script = Script(
        project_id=payload.project_id, product_id=product.id,
        creator_id=creator.id if creator else None,
        template=payload.template, duration_seconds=payload.duration_seconds,
        tone=payload.tone,
        hook=data.get("hook", ""), body=data.get("body", ""),
        cta=data.get("cta", ""), full_text=data.get("full_text", ""),
    )
    db.add(script)
    db.commit()
    db.refresh(script)
    return {
        "id": script.id,
        "hook": script.hook, "body": script.body, "cta": script.cta,
        "full_text": script.full_text,
    }


class ScriptRewriteRequest(BaseModel):
    script_id: Optional[int] = None
    full_text: str
    instruction: str


@router.post("/api/scripts/rewrite", dependencies=[Depends(require_login_api)])
async def api_rewrite_script(payload: ScriptRewriteRequest, db: Session = Depends(get_db)):
    api_key = get_config(db, "GEMINI_API_KEY")
    model = get_config(db, "GEMINI_MODEL", "gemini-2.0-flash")
    if not api_key:
        raise HTTPException(400, "Gemini API key is not configured.")
    try:
        new_text = rewrite_script(api_key, model, payload.full_text, payload.instruction)
    except GeminiError as exc:
        raise HTTPException(502, f"Gemini request failed: {exc}")
    if payload.script_id:
        s = db.get(Script, payload.script_id)
        if s:
            s.full_text = new_text
            db.commit()
    return {"full_text": new_text}


@router.post("/api/scripts/{script_id}", dependencies=[Depends(require_login_api)])
async def api_update_script(script_id: int,
                             hook: str = Form(""), body: str = Form(""),
                             cta: str = Form(""), full_text: str = Form(""),
                             db: Session = Depends(get_db)):
    s = db.get(Script, script_id)
    if not s:
        raise HTTPException(404, "Script not found")
    s.hook, s.body, s.cta, s.full_text = hook, body, cta, full_text
    db.commit()
    return {"ok": True}


class HookRequest(BaseModel):
    product_id: int
    count: int = 5


@router.post("/api/scripts/hooks", dependencies=[Depends(require_login_api)])
async def api_hooks(req: HookRequest, db: Session = Depends(get_db)):
    product = db.get(Product, req.product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    api_key = get_config(db, "GEMINI_API_KEY")
    model = get_config(db, "GEMINI_MODEL", "gemini-2.0-flash")
    if not api_key:
        raise HTTPException(400, "Gemini API key is not configured.")
    try:
        hooks = generate_hooks(api_key, model, product.name,
                                product.analyzed_audience or product.target_audience,
                                n=req.count)
    except GeminiError as exc:
        raise HTTPException(502, f"Gemini request failed: {exc}")
    return {"hooks": hooks}


class CtaRequest(BaseModel):
    product_id: int


@router.post("/api/scripts/cta", dependencies=[Depends(require_login_api)])
async def api_cta(req: CtaRequest, db: Session = Depends(get_db)):
    product = db.get(Product, req.product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    api_key = get_config(db, "GEMINI_API_KEY")
    model = get_config(db, "GEMINI_MODEL", "gemini-2.0-flash")
    if not api_key:
        raise HTTPException(400, "Gemini API key is not configured.")
    try:
        cta = generate_cta(api_key, model, product.name, product.website)
    except GeminiError as exc:
        raise HTTPException(502, f"Gemini request failed: {exc}")
    return {"cta": cta}
