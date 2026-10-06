from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database import get_db
from app.models.project import Project
from app.models.product import Product
from app.models.video import VideoGeneration
from app.deps import require_login, require_login_api

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/projects", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def projects_page(request: Request, db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(desc(Project.updated_at)).all()
    return templates.TemplateResponse(request, "projects.html", {"request": request, "projects": projects})


@router.get("/projects/{project_id}", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def project_detail(project_id: int, request: Request, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    product = db.get(Product, project.product_id) if project.product_id else None
    videos = db.query(VideoGeneration).filter(VideoGeneration.project_id == project_id)\
        .order_by(desc(VideoGeneration.created_at)).all()
    return templates.TemplateResponse(request, "project_detail.html", {
        "request": request, "project": project, "product": product, "videos": videos,
    })


@router.post("/api/projects", dependencies=[Depends(require_login_api)])
async def api_create_project(
    name: str = Form(...),
    description: str = Form(""),
    product_id: int = Form(None),
    db: Session = Depends(get_db),
):
    project = Project(name=name.strip(), description=description.strip(),
                      product_id=product_id or None)
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"id": project.id}


@router.post("/api/projects/{project_id}", dependencies=[Depends(require_login_api)])
async def api_update_project(
    project_id: int,
    name: str = Form(...),
    description: str = Form(""),
    product_id: int = Form(None),
    db: Session = Depends(get_db),
):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    p.name = name.strip()
    p.description = description.strip()
    p.product_id = product_id or None
    db.commit()
    return {"ok": True}


@router.post("/api/projects/{project_id}/duplicate", dependencies=[Depends(require_login_api)])
async def api_duplicate_project(project_id: int, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    clone = Project(name=f"{p.name} (copy)", description=p.description, product_id=p.product_id)
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return {"id": clone.id}


@router.delete("/api/projects/{project_id}", dependencies=[Depends(require_login_api)])
async def api_delete_project(project_id: int, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    db.delete(p)
    db.commit()
    return {"ok": True}
