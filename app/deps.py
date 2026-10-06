"""Shared FastAPI dependencies."""
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse


def require_login(request: Request):
    """Dependency that requires an authenticated session."""
    if not request.session.get("user"):
        # Return a redirect by raising a special exception. For API routes,
        # convert to a 401 via `require_login_api`.
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"},
        )


def require_login_api(request: Request):
    if not request.session.get("user"):
        raise HTTPException(status_code=401, detail="Not authenticated")
