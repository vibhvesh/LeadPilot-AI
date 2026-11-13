"""Bearer-token API used by the external Grok Bot."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.bot.requests import add_leads, claim_request, complete_request, list_requests
from app.bot.tokens import require_bot
from app.core.database import get_db

router = APIRouter(prefix="/api/bot")


def bot_token(request: Request, db: Session = Depends(get_db)):
    return require_bot(request, db)


@router.get("/requests")
def get_requests(status: str | None = "pending", db: Session = Depends(get_db), _token=Depends(bot_token)):
    return list_requests(db, status=status or None)


@router.post("/requests/{request_id}/claim")
def post_claim(request_id: int, db: Session = Depends(get_db), token=Depends(bot_token)):
    return claim_request(db, token, request_id)


@router.post("/requests/{request_id}/complete")
def post_complete(request_id: int, body: dict, db: Session = Depends(get_db), token=Depends(bot_token)):
    return complete_request(db, token, request_id, str(body.get("notes") or ""))


@router.post("/leads")
def post_leads(body: dict, db: Session = Depends(get_db), token=Depends(bot_token)):
    return add_leads(db, token, int(body.get("request_id") or 0), body.get("leads") or [])
