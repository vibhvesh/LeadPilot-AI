"""Sign-in routes for Google and the local demo identity."""

from pathlib import Path

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth.service import client_ip, establish_identity, issue_session, revoke_request_session
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import permission_map
from app.providers.llm import select_provider
from app.search.providers import choose_search_provider

router = APIRouter()
WEB = Path(__file__).resolve().parents[1] / "web"

_oauth = OAuth()


def _google():
    settings = get_settings()
    if not settings.google_enabled:
        return None
    if "google" not in _oauth._clients:
        _oauth.register(
            name="google",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            server_metadata_url=settings.google_discovery_url,
            client_kwargs={"scope": "openid email profile"},
        )
    return _oauth.google


def _set_session_cookie(response, raw_token: str):
    settings = get_settings()
    response.set_cookie(
        settings.session_cookie_name,
        raw_token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/api/auth/config")
def auth_config():
    settings = get_settings()
    payload = {
        "demo_mode": settings.demo_mode,
        "google_enabled": settings.google_enabled,
        "product": "CanberraAI LeadPilot",
    }
    if settings.demo_mode:
        payload["demo_super_admin"] = settings.super_admin
    return payload


@router.post("/auth/demo/login")
def demo_login(body: dict, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.demo_mode:
        return JSONResponse({"detail": "Demo sign-in is disabled"}, status_code=403)
    email = str(body.get("email") or "").strip().lower()
    name = str(body.get("name") or "").strip()
    if "@" not in email or "." not in email.split("@")[-1]:
        return JSONResponse({"detail": "Enter a valid email address"}, status_code=400)
    user, outcome = establish_identity(db, email=email, name=name, ip_address=client_ip(request))
    if outcome == "pending":
        return {
            "status": "pending",
            "message": "Your account is waiting for an administrator to approve it.",
        }
    if outcome == "rejected":
        return JSONResponse(
            {"status": "rejected", "detail": "An administrator has not approved this account."},
            status_code=403,
        )
    raw = issue_session(db, user, request)
    response = JSONResponse(
        {"status": "approved", "user": {"email": user.email, "name": user.display_name, "role": user.role}}
    )
    return _set_session_cookie(response, raw)


@router.get("/auth/google/login")
async def google_login(request: Request):
    settings = get_settings()
    google = _google()
    if google is None:
        return HTMLResponse(_page("Google sign-in is not configured", "Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET on the server, then restart LeadPilot."), status_code=503)
    return await google.authorize_redirect(request, settings.redirect_uri(), code_challenge_method="S256")


@router.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    google = _google()
    if google is None:
        return HTMLResponse(_page("Google sign-in is not configured", "The OAuth client is missing on the server."), status_code=503)
    try:
        token = await google.authorize_access_token(request)
        userinfo = token.get("userinfo") or await google.userinfo(token=token)
    except Exception:
        request.session.clear()
        return HTMLResponse(_page("Google sign-in failed", "Please try again, or contact an administrator."), status_code=401)
    email = str(userinfo.get("email") or "").strip().lower()
    verified = userinfo.get("email_verified") is True or str(userinfo.get("email_verified", "")).lower() == "true"
    if not email or not verified:
        request.session.clear()
        return HTMLResponse(_page("Access denied", "Google must confirm your email address."), status_code=403)
    user, outcome = establish_identity(
        db,
        email=email,
        name=str(userinfo.get("name") or email),
        google_sub=str(userinfo.get("sub") or "") or None,
        ip_address=client_ip(request),
    )
    request.session.clear()
    if outcome == "pending":
        return HTMLResponse((WEB / "pending.html").read_text(encoding="utf-8"), status_code=200)
    if outcome != "approved":
        return HTMLResponse(_page("Access not approved", "An administrator has not approved this account."), status_code=403)
    raw = issue_session(db, user, request)
    response = RedirectResponse(url="/", status_code=302)
    return _set_session_cookie(response, raw)


@router.post("/auth/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    revoke_request_session(db, request)
    settings = get_settings()
    response = JSONResponse({"status": "signed_out"})
    response.delete_cookie(settings.session_cookie_name, path="/")
    return response


@router.get("/api/me")
def me(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    settings = get_settings()
    from sqlalchemy import func, select

    from app.core.permissions import has_permission
    from app.models import User

    llm_provider, llm_model, llm_note = select_provider(db)
    try:
        search_provider, _key = choose_search_provider(db)
    except Exception:
        search_provider = settings.search_provider
    pending_users = None
    if has_permission(db, user, "users"):
        pending_users = db.scalar(select(func.count()).select_from(User).where(User.status == "pending")) or 0
    return {
        "id": user.id,
        "email": user.email,
        "name": user.display_name,
        "role": user.role,
        "status": user.status,
        "permissions": permission_map(db, user),
        "pending_users": pending_users,
        "demo_mode": settings.demo_mode,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "llm_note": llm_note,
        "search_provider": search_provider,
    }


def _page(title: str, message: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>LeadPilot</title></head>"
        f"<body style='font-family:Segoe UI,Arial;background:#f4f6fa;padding:48px'>"
        f"<h2>{title}</h2><p>{message}</p><p><a href='/login'>Back to sign in</a></p></body></html>"
    )
