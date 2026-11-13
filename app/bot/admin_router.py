"""Admins create Grok Bot tokens from workspace settings."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.audit.service import record
from app.bot.requests import create_request, list_requests
from app.bot.tokens import create_token, list_tokens, revoke_token
from app.core.database import get_db
from app.core.deps import require_module

router = APIRouter()


@router.get("/api/settings/bot-tokens")
def get_tokens(db: Session = Depends(get_db), _user=Depends(require_module("settings"))):
    return list_tokens(db)


@router.post("/api/settings/bot-tokens")
def post_token(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("settings", manage=True))):
    created = create_token(db, actor, str(body.get("name") or ""))
    record(db, user=actor, action="bot_token_created", module="settings", target=str(created["id"]), detail={"hint": created["hint"]})
    db.commit()
    return created


@router.delete("/api/settings/bot-tokens/{token_id}")
def delete_token(token_id: int, db: Session = Depends(get_db), actor=Depends(require_module("settings", manage=True))):
    revoked = revoke_token(db, token_id)
    record(db, user=actor, action="bot_token_revoked", module="settings", target=str(token_id), detail={"hint": revoked["hint"]})
    db.commit()
    return revoked


@router.post("/api/search/deep")
def post_deep(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("search", manage=True))):
    return create_request(db, actor, str(body.get("text") or ""))


@router.get("/api/search/deep")
def get_deep(db: Session = Depends(get_db), _user=Depends(require_module("search"))):
    return list_requests(db)
