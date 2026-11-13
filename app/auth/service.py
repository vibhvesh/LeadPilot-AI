"""Google and demo identity resolution, plus opaque server-side sessions."""

from datetime import timedelta

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.config import get_settings
from app.core.security import hash_token, new_token
from app.models import SessionToken, User
from app.models.identity import utcnow


def client_ip(request: Request | None) -> str:
    if request is None:
        return ""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:80]
    if request.client and request.client.host:
        return request.client.host
    return ""


def establish_identity(
    db: Session,
    *,
    email: str,
    name: str = "",
    google_sub: str | None = None,
    ip_address: str = "",
) -> tuple[User, str]:
    """Return the user and one of: approved, pending, rejected."""
    settings = get_settings()
    normalized = email.strip().lower()
    display = (name or normalized).strip()[:250]
    is_super = normalized == settings.super_admin
    user = db.scalar(select(User).where(User.email == normalized))
    if user is None and google_sub:
        user = db.scalar(select(User).where(User.google_sub == google_sub))

    if user is None:
        user = User(
            email=normalized,
            display_name=display,
            google_sub=google_sub,
            role="super_admin" if is_super else "member",
            status="approved" if is_super else "pending",
        )
        db.add(user)
        db.flush()
        outcome = "approved" if is_super else "pending"
        record(
            db,
            user=user,
            email=normalized,
            action="access_request" if outcome == "pending" else "sign_in",
            module="users",
            target=normalized,
            detail={"outcome": outcome},
            ip_address=ip_address,
            success=outcome == "approved",
        )
    else:
        if google_sub and not user.google_sub:
            user.google_sub = google_sub
        if display and display != normalized:
            user.display_name = display
        if user.email != normalized:
            user.email = normalized
        if is_super:
            user.role = "super_admin"
            user.status = "approved"
        if user.status == "approved":
            outcome = "approved"
        elif user.status == "rejected":
            outcome = "rejected"
            record(
                db,
                user=user,
                action="sign_in_denied",
                module="users",
                target=normalized,
                detail={"reason": "rejected"},
                success=False,
                ip_address=ip_address,
            )
        else:
            outcome = "pending"
            record(
                db,
                user=user,
                action="access_request",
                module="users",
                target=normalized,
                detail={"outcome": "pending"},
                success=False,
                ip_address=ip_address,
            )
    db.commit()
    db.refresh(user)
    return user, outcome


def issue_session(db: Session, user: User, request: Request | None = None) -> str:
    settings = get_settings()
    raw = new_token()
    db.add(
        SessionToken(
            token_hash=hash_token(raw),
            user_id=user.id,
            expires_at=utcnow() + timedelta(seconds=settings.session_max_age_seconds),
            revoked=False,
            ip_address=client_ip(request),
            user_agent=(request.headers.get("user-agent", "")[:300] if request else ""),
        )
    )
    user.last_login_at = utcnow()
    record(
        db,
        user=user,
        action="sign_in",
        module="users",
        target=user.email,
        detail={"role": user.role},
        ip_address=client_ip(request),
    )
    db.commit()
    return raw


def user_from_raw_token(db: Session, raw_token: str | None) -> User | None:
    if not raw_token:
        return None
    record_row = db.scalar(select(SessionToken).where(SessionToken.token_hash == hash_token(raw_token)))
    if record_row is None or record_row.revoked:
        return None
    expires = record_row.expires_at
    if expires.tzinfo is None:
        from datetime import timezone

        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= utcnow():
        return None
    user = db.get(User, record_row.user_id)
    if user is None:
        return None
    return user


def user_from_request(db: Session, request: Request) -> User | None:
    settings = get_settings()
    raw = request.cookies.get(settings.session_cookie_name)
    return user_from_raw_token(db, raw)


def revoke_request_session(db: Session, request: Request) -> None:
    settings = get_settings()
    raw = request.cookies.get(settings.session_cookie_name)
    if not raw:
        return
    row = db.scalar(select(SessionToken).where(SessionToken.token_hash == hash_token(raw)))
    if row is not None:
        row.revoked = True
        user = db.get(User, row.user_id)
        record(db, user=user, action="sign_out", module="users", target=getattr(user, "email", ""), ip_address=client_ip(request))
        db.commit()


def revoke_user_sessions(db: Session, user_id: int) -> None:
    rows = db.scalars(select(SessionToken).where(SessionToken.user_id == user_id, SessionToken.revoked.is_(False))).all()
    for row in rows:
        row.revoked = True
