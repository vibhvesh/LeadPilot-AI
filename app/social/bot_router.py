"""Bot-token ingest and read for the Social feed. Same auth as /api/bot/leads."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.bot.tokens import require_bot
from app.core.database import get_db
from app.core.errors import AppError
from app.social.service import ingest_items, list_for_bot

router = APIRouter(prefix="/api/bot")


def bot_token(request: Request, db: Session = Depends(get_db)):
    return require_bot(request, db)


@router.get("/social")
def get_social(status: str | None = None, db: Session = Depends(get_db), _token=Depends(bot_token)):
    return list_for_bot(db, status)


@router.post("/social")
def post_social(body: dict, db: Session = Depends(get_db), token=Depends(bot_token)):
    request_id = body.get("request_id")
    return ingest_items(
        db,
        items_from_body(body),
        source="bot",
        token=token,
        request_id=int(request_id) if str(request_id or "").isdigit() else None,
    )


def items_from_body(body: dict) -> list:
    if not isinstance(body, dict):
        raise AppError("Send social items as JSON")
    if "items" in body:
        items = body.get("items")
        if not isinstance(items, list):
            raise AppError("items must be a list")
        return items
    if body.get("url") or body.get("post_url") or body.get("link"):
        return [body]
    raise AppError("Send at least one social item")
