"""UGCORA Studio - FastAPI application entry point."""
import os
import logging
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ugcora")

from app.models.database import init_db, SessionLocal
from app.services.auth_service import ensure_admin_user
from app.services.seed_service import seed_creators

from app.routes import (
    auth as auth_routes,
    dashboard as dashboard_routes,
    products as products_routes,
    projects as projects_routes,
    creators as creators_routes,
    scripts as scripts_routes,
    videos as videos_routes,
    settings as settings_routes,
    ai as ai_routes,
)


def create_app() -> FastAPI:
    app = FastAPI(title="UGCORA Studio", docs_url=None, redoc_url=None)

    session_secret = os.getenv("SESSION_SECRET", "dev-secret-change-me")
    app.add_middleware(SessionMiddleware, secret_key=session_secret, same_site="lax")

    # Static files
    Path("app/static").mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    # Serve local data (product images, creator avatars, generated videos)
    Path("data").mkdir(parents=True, exist_ok=True)
    app.mount("/data", StaticFiles(directory="data"), name="data")

    # Init DB and seed
    init_db()
    db = SessionLocal()
    try:
        ensure_admin_user(db)
        seed_creators(db)
    finally:
        db.close()

    # Routes
    app.include_router(auth_routes.router)
    app.include_router(dashboard_routes.router)
    app.include_router(products_routes.router)
    app.include_router(projects_routes.router)
    app.include_router(creators_routes.router)
    app.include_router(scripts_routes.router)
    app.include_router(videos_routes.router)
    app.include_router(settings_routes.router)
    app.include_router(ai_routes.router)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # Redirect browser requests back to /login on 307 with Location header
        if exc.status_code == 307 and "Location" in (exc.headers or {}):
            return RedirectResponse(exc.headers["Location"], status_code=303)
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        raise exc

    @app.get("/healthz")
    async def healthz():
        return {"ok": True, "app": "UGCORA Studio"}

    return app


app = create_app()
