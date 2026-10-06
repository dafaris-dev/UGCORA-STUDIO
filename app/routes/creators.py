from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database import get_db
from app.models.creator import Creator
from app.deps import require_login, require_login_api
from app.services.file_service import save_upload, delete_file, ALLOWED_IMAGE_EXT

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

CATEGORIES = ["Female", "Male", "Lifestyle", "Professional", "Fitness",
              "Beauty", "Fashion", "Technology", "Business"]


@router.get("/creators", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def creators_page(request: Request, category: str = "", db: Session = Depends(get_db)):
    q = db.query(Creator)
    if category:
        q = q.filter((Creator.category == category) | (Creator.gender == category))
    creators = q.order_by(desc(Creator.favorite), Creator.name).all()
    return templates.TemplateResponse(request, "creators.html", {
        "request": request, "creators": creators,
        "categories": CATEGORIES, "active_category": category,
    })


@router.post("/api/creators", dependencies=[Depends(require_login_api)])
async def api_create_creator(
    name: str = Form(...),
    category: str = Form("Lifestyle"),
    gender: str = Form("Female"),
    style: str = Form(""),
    personality: str = Form(""),
    age_appearance: str = Form(""),
    language: str = Form("English"),
    default_voice: str = Form(""),
    description: str = Form(""),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    c = Creator(
        name=name.strip(), category=category, gender=gender, style=style,
        personality=personality, age_appearance=age_appearance,
        language=language, default_voice=default_voice, description=description,
    )
    try:
        if image and image.filename:
            c.image_path = save_upload(image, "creators", ALLOWED_IMAGE_EXT)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id}


@router.get("/api/creators", dependencies=[Depends(require_login_api)])
async def api_list_creators(db: Session = Depends(get_db)):
    creators = db.query(Creator).order_by(desc(Creator.favorite), Creator.name).all()
    return [
        {"id": c.id, "name": c.name, "category": c.category, "gender": c.gender,
         "style": c.style, "personality": c.personality, "image_path": c.image_path,
         "favorite": c.favorite}
        for c in creators
    ]


@router.post("/api/creators/{creator_id}", dependencies=[Depends(require_login_api)])
async def api_update_creator(
    creator_id: int,
    name: str = Form(...),
    category: str = Form("Lifestyle"),
    gender: str = Form("Female"),
    style: str = Form(""),
    personality: str = Form(""),
    age_appearance: str = Form(""),
    language: str = Form("English"),
    default_voice: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    c = db.get(Creator, creator_id)
    if not c:
        raise HTTPException(404, "Creator not found")
    for k, v in {
        "name": name, "category": category, "gender": gender, "style": style,
        "personality": personality, "age_appearance": age_appearance,
        "language": language, "default_voice": default_voice, "description": description,
    }.items():
        setattr(c, k, v)
    db.commit()
    return {"ok": True}


@router.post("/api/creators/{creator_id}/favorite", dependencies=[Depends(require_login_api)])
async def api_toggle_favorite(creator_id: int, db: Session = Depends(get_db)):
    c = db.get(Creator, creator_id)
    if not c:
        raise HTTPException(404, "Creator not found")
    c.favorite = not c.favorite
    db.commit()
    return {"favorite": c.favorite}


@router.delete("/api/creators/{creator_id}", dependencies=[Depends(require_login_api)])
async def api_delete_creator(creator_id: int, db: Session = Depends(get_db)):
    c = db.get(Creator, creator_id)
    if not c:
        raise HTTPException(404, "Creator not found")
    delete_file(c.image_path)
    db.delete(c)
    db.commit()
    return {"ok": True}
