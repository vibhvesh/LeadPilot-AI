from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth, OAuthError
from app.core.config import settings
from app.core.database import get_db
from app.models import User, UserSession, Role, AuditLog
from app.core.security import new_session_token, token_digest

router = APIRouter(prefix="/auth", tags=["authentication"])
oauth = OAuth()
if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

SESSION_COOKIE = "leadpilot_session"
SESSION_DAYS = 7

def cookie_options():
    production = settings.app_env.lower() == "production"
    return {"httponly": True, "secure": production, "samesite": "lax", "path": "/", "max_age": SESSION_DAYS * 86400}

@router.get("/google/login")
async def google_login(request: Request):
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")
    redirect_uri = settings.google_redirect_uri
    return await oauth.google.authorize_redirect(request, redirect_uri, prompt="select_account")

@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
        profile = token.get("userinfo")
        if not profile:
            profile = await oauth.google.parse_id_token(request, token)
    except (OAuthError, Exception):
        return RedirectResponse(settings.frontend_url + "/?auth=error", status_code=303)

    email = (profile.get("email") or "").strip().lower()
    google_sub = profile.get("sub")
    if not email or not google_sub or profile.get("email_verified") is not True:
        return RedirectResponse(settings.frontend_url + "/?auth=unverified", status_code=303)

    is_super_admin = email == settings.super_admin_email.lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, google_sub=google_sub,
                    full_name=profile.get("name"), avatar_url=profile.get("picture"),
                    status="active" if is_super_admin else "pending",
                    is_super_admin=is_super_admin)
        db.add(user)
        db.flush()
    else:
        if user.google_sub and user.google_sub != google_sub:
            raise HTTPException(status_code=403, detail="Google identity does not match this account")
        user.google_sub = google_sub
        user.full_name = profile.get("name") or user.full_name
        user.avatar_url = profile.get("picture") or user.avatar_url
        if is_super_admin:
            user.is_super_admin = True
            user.status = "active"
    if user.status != "active":
        db.add(AuditLog(action="auth.login_pending", target_type="user", target_id=str(user.id)))
        db.commit()
        return RedirectResponse(settings.frontend_url + "/?auth=pending", status_code=303)

    if is_super_admin:
        admin_role = db.scalar(select(Role).where(Role.name == "Super Admin"))
        if admin_role and admin_role not in user.roles:
            user.roles.append(admin_role)

    raw_token = new_session_token()
    session = UserSession(user_id=user.id, token_hash=token_digest(raw_token),
                          expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS))
    db.add(session)
    db.add(AuditLog(actor_user_id=user.id, action="auth.login", target_type="user", target_id=str(user.id)))
    db.commit()
    response = RedirectResponse(settings.frontend_url + "/?auth=success", status_code=303)
    response.set_cookie(SESSION_COOKIE, raw_token, **cookie_options())
    return response

def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    raw_token = request.cookies.get(SESSION_COOKIE)
    if not raw_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    record = db.scalar(select(UserSession).where(
        UserSession.token_hash == token_digest(raw_token),
        UserSession.revoked_at.is_(None),
        UserSession.expires_at > datetime.now(timezone.utc)))
    if not record:
        raise HTTPException(status_code=401, detail="Session expired")
    user = db.get(User, record.user_id)
    if not user or user.status != "active":
        raise HTTPException(status_code=403, detail="Account is not active")
    return user

@router.get("/me")
def who_am_i(user: User = Depends(current_user)):
    return {"id": str(user.id), "email": user.email, "name": user.full_name,
            "avatar": user.avatar_url, "status": user.status,
            "is_super_admin": user.is_super_admin,
            "roles": [role.name for role in user.roles]}

@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_token = request.cookies.get(SESSION_COOKIE)
    if raw_token:
        record = db.scalar(select(UserSession).where(UserSession.token_hash == token_digest(raw_token)))
        if record and record.revoked_at is None:
            record.revoked_at = datetime.now(timezone.utc)
            db.add(AuditLog(actor_user_id=record.user_id, action="auth.logout", target_type="user", target_id=str(record.user_id)))
            db.commit()
    result = Response(status_code=204)
    result.delete_cookie(SESSION_COOKIE, path="/", httponly=True, secure=settings.app_env.lower() == "production", samesite="lax")
    return result
