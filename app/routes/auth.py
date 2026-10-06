from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.services.auth_service import authenticate

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"request": request, "error": None})


@router.post("/login")
async def login_submit(request: Request,
                        username: str = Form(...),
                        password: str = Form(...),
                        db: Session = Depends(get_db)):
    if authenticate(db, username, password):
        request.session["user"] = username
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"request": request, "error": "Invalid credentials."},
        status_code=401,
    )


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
