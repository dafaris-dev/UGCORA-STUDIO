from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database import get_db
from app.models.product import Product
from app.deps import require_login, require_login_api
from app.services.file_service import save_upload, delete_file, ALLOWED_IMAGE_EXT, ALLOWED_VIDEO_EXT
from app.services.config_service import get_config
from app.services.gemini_service import analyze_product, GeminiError

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/products", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def products_page(request: Request, db: Session = Depends(get_db)):
    products = db.query(Product).order_by(desc(Product.updated_at)).all()
    return templates.TemplateResponse(request, "products.html", {"request": request, "products": products})


@router.get("/products/{product_id}", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def product_detail(product_id: int, request: Request, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    return templates.TemplateResponse(request, "product_detail.html", {"request": request, "product": product})


# -------- API --------

@router.post("/api/products", dependencies=[Depends(require_login_api)])
async def api_create_product(
    name: str = Form(...),
    description: str = Form(""),
    benefits: str = Form(""),
    target_audience: str = Form(""),
    website: str = Form(""),
    cta: str = Form(""),
    image: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    logo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    product = Product(
        name=name.strip(),
        description=description.strip(),
        benefits=benefits.strip(),
        target_audience=target_audience.strip(),
        website=website.strip(),
        cta=cta.strip(),
    )
    try:
        if image and image.filename:
            product.image_path = save_upload(image, "products", ALLOWED_IMAGE_EXT)
        if video and video.filename:
            product.video_path = save_upload(video, "products", ALLOWED_VIDEO_EXT)
        if logo and logo.filename:
            product.logo_path = save_upload(logo, "products", ALLOWED_IMAGE_EXT)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    db.add(product)
    db.commit()
    db.refresh(product)
    return {"id": product.id}


@router.get("/api/products", dependencies=[Depends(require_login_api)])
async def api_list_products(db: Session = Depends(get_db)):
    products = db.query(Product).order_by(desc(Product.updated_at)).all()
    return [
        {"id": p.id, "name": p.name, "description": p.description,
         "image_path": p.image_path, "cta": p.cta}
        for p in products
    ]


@router.get("/api/products/{product_id}", dependencies=[Depends(require_login_api)])
async def api_get_product(product_id: int, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    return {c.name: getattr(p, c.name) for c in p.__table__.columns}


@router.post("/api/products/{product_id}", dependencies=[Depends(require_login_api)])
async def api_update_product(
    product_id: int,
    name: str = Form(...),
    description: str = Form(""),
    benefits: str = Form(""),
    target_audience: str = Form(""),
    website: str = Form(""),
    cta: str = Form(""),
    category: str = Form(""),
    analyzed_audience: str = Form(""),
    customer_problem: str = Form(""),
    main_benefits: str = Form(""),
    usp: str = Form(""),
    marketing_angle: str = Form(""),
    ugc_hook: str = Form(""),
    recommended_cta: str = Form(""),
    db: Session = Depends(get_db),
):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    for k, v in {
        "name": name, "description": description, "benefits": benefits,
        "target_audience": target_audience, "website": website, "cta": cta,
        "category": category, "analyzed_audience": analyzed_audience,
        "customer_problem": customer_problem, "main_benefits": main_benefits,
        "usp": usp, "marketing_angle": marketing_angle, "ugc_hook": ugc_hook,
        "recommended_cta": recommended_cta,
    }.items():
        setattr(p, k, v.strip() if isinstance(v, str) else v)
    db.commit()
    return {"ok": True}


@router.delete("/api/products/{product_id}", dependencies=[Depends(require_login_api)])
async def api_delete_product(product_id: int, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    for path in (p.image_path, p.video_path, p.logo_path):
        delete_file(path)
    db.delete(p)
    db.commit()
    return {"ok": True}


@router.post("/api/products/{product_id}/analyze", dependencies=[Depends(require_login_api)])
async def api_analyze_product(product_id: int, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")

    api_key = get_config(db, "GEMINI_API_KEY")
    model = get_config(db, "GEMINI_MODEL", "gemini-2.0-flash")
    if not api_key:
        raise HTTPException(400, "Gemini API key is not configured.")

    try:
        data = analyze_product(
            api_key, model,
            {
                "name": p.name, "description": p.description, "benefits": p.benefits,
                "target_audience": p.target_audience, "website": p.website, "cta": p.cta,
            },
            image_path=p.image_path or None,
        )
    except GeminiError as exc:
        raise HTTPException(502, f"Gemini request failed: {exc}")

    p.category = data.get("category", p.category) or p.category
    p.analyzed_audience = data.get("target_audience", p.analyzed_audience) or p.analyzed_audience
    p.customer_problem = data.get("customer_problem", p.customer_problem) or p.customer_problem
    p.main_benefits = data.get("main_benefits", p.main_benefits) or p.main_benefits
    p.usp = data.get("usp", p.usp) or p.usp
    p.marketing_angle = data.get("marketing_angle", p.marketing_angle) or p.marketing_angle
    p.ugc_hook = data.get("ugc_hook", p.ugc_hook) or p.ugc_hook
    p.recommended_cta = data.get("recommended_cta", p.recommended_cta) or p.recommended_cta
    db.commit()
    return {
        "category": p.category,
        "analyzed_audience": p.analyzed_audience,
        "customer_problem": p.customer_problem,
        "main_benefits": p.main_benefits,
        "usp": p.usp,
        "marketing_angle": p.marketing_angle,
        "ugc_hook": p.ugc_hook,
        "recommended_cta": p.recommended_cta,
    }
