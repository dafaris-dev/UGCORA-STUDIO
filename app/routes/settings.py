from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.deps import require_login, require_login_api
from app.services.config_service import (
    PROVIDER_SECTIONS, get_config, set_config, delete_config,
    provider_status, SETTING_KEYS,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _default_select_for(section_key: str) -> str:
    return {
        "llm": "LLM_PROVIDER",
        "video": "VIDEO_PROVIDER",
        "voice": "VOICE_PROVIDER",
        "image": "IMAGE_PROVIDER",
        "storage": "STORAGE_PROVIDER",
    }.get(section_key, "")


@router.get("/settings", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def settings_page(request: Request, db: Session = Depends(get_db)):
    # Build per-provider display dict
    sections = []
    for section_key, section_name, section_desc, providers in PROVIDER_SECTIONS:
        rows = []
        for p in providers:
            status = provider_status(db, p)
            rows.append({**p, "status": status})
        sections.append({
            "key": section_key,
            "name": section_name,
            "desc": section_desc,
            "default_key": _default_select_for(section_key),
            "default_value": get_config(db, _default_select_for(section_key), ""),
            "providers": rows,
        })

    preferences = {
        "DEFAULT_ASPECT":   get_config(db, "DEFAULT_ASPECT", "9:16"),
        "DEFAULT_DURATION": get_config(db, "DEFAULT_DURATION", "30"),
        "APP_ENV":          get_config(db, "APP_ENV", "production"),
    }

    return templates.TemplateResponse(request, "settings.html", {
        "request": request,
        "sections": sections,
        "preferences": preferences,
    })


@router.post("/api/settings", dependencies=[Depends(require_login_api)])
async def api_update_settings(request: Request, db: Session = Depends(get_db)):
    """Accept any valid key from the catalog. Blank secret inputs are IGNORED
    (so re-saving the page doesn't wipe keys the user left masked)."""
    form = await request.form()
    reset_keys = set(form.getlist("reset"))

    for raw_key, raw_value in form.multi_items():
        if raw_key == "reset":
            continue
        if raw_key not in SETTING_KEYS:
            continue
        value = (raw_value or "").strip()
        is_secret = raw_key.endswith(("_API_KEY", "_SECRET", "_SECRET_KEY", "_SERVICE_ROLE",
                                       "_SERVICE_ACCOUNT_JSON", "_USER_ID"))
        # Blank secret → keep whatever was already stored
        if is_secret and not value:
            continue
        set_config(db, raw_key, value)

    # Explicit resets wipe the stored value
    for k in reset_keys:
        if k in SETTING_KEYS:
            delete_config(db, k)

    return {"ok": True}


@router.post("/api/settings/reset", dependencies=[Depends(require_login_api)])
async def api_reset_one(request: Request, db: Session = Depends(get_db)):
    """Shortcut to wipe a single key (used by the per-field reset button)."""
    form = await request.form()
    key = form.get("key", "").strip()
    if key and key in SETTING_KEYS:
        delete_config(db, key)
        return {"ok": True, "key": key}
    return JSONResponse({"ok": False, "error": "unknown key"}, status_code=400)
