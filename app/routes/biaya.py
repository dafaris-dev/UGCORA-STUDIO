"""Biaya (cost/token) tracker page."""
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import csv
import io

from app.models.database import get_db
from app.deps import require_login, require_login_api
from app.services import token_tracker

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/biaya", response_class=HTMLResponse, dependencies=[Depends(require_login)])
async def biaya_page(request: Request, days: int = Query(30, ge=1, le=365),
                     db: Session = Depends(get_db)):
    s = token_tracker.summary(db, days=days)
    return templates.TemplateResponse(request, "biaya.html",
                                      {"request": request, "s": s, "days": days})


@router.get("/api/biaya/export", dependencies=[Depends(require_login_api)])
async def biaya_export(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    s = token_tracker.summary(db, days=days)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["when", "agent", "product", "provider", "model",
                "input_tokens", "output_tokens", "total_tokens", "free"])
    for r in s["recent"]:
        w.writerow([r["when"], r["agent"], r["product"], r["provider"], r["model"],
                     r["input"], r["output"], r["total"], "yes" if r["free"] else "no"])
    return PlainTextResponse(buf.getvalue(), media_type="text/csv",
                              headers={"Content-Disposition": f"attachment; filename=ugcora-tokens-{days}d.csv"})
