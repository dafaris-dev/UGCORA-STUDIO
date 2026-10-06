from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.deps import require_login, require_login_api
from app.services.config_service import get_config, set_config, mask_secret, SETTING_KEYS

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/settings", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def settings_page(request: Request, db: Session = Depends(get_db)):
    data = {
        "GEMINI_API_KEY": mask_secret(get_config(db, "GEMINI_API_KEY")),
        "GEMINI_MODEL": get_config(db, "GEMINI_MODEL", "gemini-2.0-flash"),
        "NVIDIA_API_KEY": mask_secret(get_config(db, "NVIDIA_API_KEY")),
        "NVIDIA_MODEL": get_config(db, "NVIDIA_MODEL"),
        "NVIDIA_BASE_URL": get_config(db, "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        "VIDEO_PROVIDER": get_config(db, "VIDEO_PROVIDER", "nvidia"),
        "VOICE_PROVIDER": get_config(db, "VOICE_PROVIDER", "none"),
    }
    return templates.TemplateResponse(request, "settings.html", {"request": request, "settings": data})


@router.post("/api/settings", dependencies=[Depends(require_login_api)])
async def api_update_settings(
    request: Request,
    GEMINI_API_KEY: str = Form(""),
    GEMINI_MODEL: str = Form(""),
    NVIDIA_API_KEY: str = Form(""),
    NVIDIA_MODEL: str = Form(""),
    NVIDIA_BASE_URL: str = Form(""),
    VIDEO_PROVIDER: str = Form(""),
    VOICE_PROVIDER: str = Form(""),
    db: Session = Depends(get_db),
):
    updates = {
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "GEMINI_MODEL": GEMINI_MODEL,
        "NVIDIA_API_KEY": NVIDIA_API_KEY,
        "NVIDIA_MODEL": NVIDIA_MODEL,
        "NVIDIA_BASE_URL": NVIDIA_BASE_URL,
        "VIDEO_PROVIDER": VIDEO_PROVIDER,
        "VOICE_PROVIDER": VOICE_PROVIDER,
    }
    for key, value in updates.items():
        if key not in SETTING_KEYS:
            continue
        # Skip blank secret fields so we don't wipe them when the UI shows the mask
        if key.endswith("_API_KEY") and not value.strip():
            continue
        set_config(db, key, value.strip())
    return {"ok": True}
