"""Create and check Grok Bot API tokens. The raw token is returned only once."""

import hmac

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_token, new_token
from app.models import BotToken
from app.models.identity import utcnow


def create_token(db: Session, actor, name: str) -> dict:
    label = (name or "").strip()
    if len(label) < 2:
        from app.core.errors import AppError

        raise AppError("Name the token")
    raw = "lpb_" + new_token()
    row = BotToken(
        name=label[:120],
        token_hash=hash_token(raw),
        hint=_hint(raw),
        created_by=actor.id,
        revoked=False,
    )
    db.add(row)
    db.flush()
    return {"id": row.id, "name": row.name, "token": raw, "hint": row.hint}


def list_tokens(db: Session) -> list[dict]:
    rows = db.scalars(select(BotToken).order_by(BotToken.id.desc())).all()
    return [_public(row) for row in rows]


def revoke_token(db: Session, token_id: int) -> dict:
    row = db.get(BotToken, token_id)
    if row is None:
        from app.core.errors import AppError

        raise AppError("Token not found", 404)
    row.revoked = True
    db.flush()
    return _public(row)


def require_bot(request: Request, db: Session) -> BotToken:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bot token required")
    raw = header.split(" ", 1)[1].strip()
    if not raw:
        raise HTTPException(status_code=401, detail="Bot token required")
    row = db.scalar(select(BotToken).where(BotToken.token_hash == hash_token(raw)))
    if row is None or row.revoked or not hmac.compare_digest(row.token_hash, hash_token(raw)):
        raise HTTPException(status_code=401, detail="Bot token is invalid")
    row.last_used_at = utcnow()
    db.flush()
    return row


def _hint(raw: str) -> str:
    return raw[:4] + "…" + raw[-4:]


def _public(row: BotToken) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "hint": row.hint,
        "revoked": row.revoked,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
    }
