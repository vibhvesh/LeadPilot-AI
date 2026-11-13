"""Pages and actions a signed-in person uses to talk to a bot."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.bot.chat import decide, list_connections, unread_count, user_messages, user_reply
from app.core.database import get_db
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/bots")


@router.get("")
def get_bots(db: Session = Depends(get_db), actor=Depends(get_current_user)):
    return list_connections(db, actor)


@router.get("/unread")
def get_unread(db: Session = Depends(get_db), actor=Depends(get_current_user)):
    return {"unread": unread_count(db, actor)}


@router.post("/{connection_id}/decision")
def post_decision(connection_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(get_current_user)):
    return decide(db, actor, connection_id, str(body.get("decision") or ""))


@router.get("/{connection_id}/messages")
def get_messages(connection_id: int, since: str | None = None, db: Session = Depends(get_db), actor=Depends(get_current_user)):
    return user_messages(db, actor, connection_id, since)


@router.post("/{connection_id}/messages")
def post_message(connection_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(get_current_user)):
    return user_reply(db, actor, connection_id, str(body.get("text") or ""))
