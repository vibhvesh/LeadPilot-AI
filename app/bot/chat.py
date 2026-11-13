"""Connection requests and the user-to-bot chat thread."""

from datetime import datetime, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.config import get_settings
from app.core.errors import AppError
from app.models import BotConnection, BotMessage, BotToken, User
from app.models.identity import utcnow

DECISIONS = {"approve": "approved", "block": "blocked", "revoke": "revoked"}


def connect_bot(db: Session, token: BotToken, payload: dict) -> dict:
    name = str(payload.get("name") or "").strip()
    if len(name) < 2:
        raise AppError("A bot name is required")
    description = str(payload.get("description") or "").strip()[:2000]
    avatar = str(payload.get("avatar_url") or "").strip()[:500]
    webhook = str(payload.get("webhook_url") or "").strip()[:500]
    row = db.scalar(select(BotConnection).where(BotConnection.token_id == token.id))
    created = row is None
    if created:
        row = BotConnection(token_id=token.id, name=name[:120], status="pending")
        db.add(row)
    elif row.status in {"blocked", "revoked"}:
        row.status = "pending"
        row.decided_by = None
        row.decided_at = None
    row.name = name[:120]
    row.description = description
    row.avatar_url = avatar
    row.webhook_url = webhook
    if created or "user_email" in payload:
        user = _target_user(db, payload.get("user_email"))
        row.user_id = user.id if user else None
    db.commit()
    db.refresh(row)
    return _bot_view(db, row)


def list_connections(db: Session, actor: User) -> list[dict]:
    rows = db.scalars(select(BotConnection).order_by(BotConnection.id.desc())).all()
    return [_user_view(db, row, actor) for row in rows if _can_see(actor, row)]


def decide(db: Session, actor: User, connection_id: int, decision: str) -> dict:
    choice = (decision or "").strip().lower()
    if choice not in DECISIONS:
        raise AppError("Decision must be approve, block, or revoke")
    row = db.get(BotConnection, connection_id)
    if row is None or not _can_see(actor, row):
        raise AppError("Bot connection not found", 404)
    if not _can_decide(actor, row):
        raise AppError("You cannot change this bot", 403)
    if choice == "approve" and row.status == "revoked":
        raise AppError("A revoked bot must request to connect again", 409)
    if choice == "revoke" and row.status == "revoked":
        raise AppError("This bot is already revoked", 409)
    row.status = DECISIONS[choice]
    row.decided_by = actor.email
    row.decided_at = utcnow()
    record(
        db,
        user=actor,
        action={"approve": "bot_approved", "block": "bot_blocked", "revoke": "bot_revoked"}[choice],
        module="bots",
        target=str(row.id),
        detail={"name": row.name, "status": row.status},
    )
    db.commit()
    db.refresh(row)
    return _user_view(db, row, actor)


def unread_count(db: Session, actor: User) -> int:
    visible = [row.id for row in db.scalars(select(BotConnection)).all() if _can_see(actor, row)]
    if not visible:
        return 0
    return db.scalar(
        select(func.count())
        .select_from(BotMessage)
        .where(
            BotMessage.connection_id.in_(visible),
            BotMessage.sender == "bot",
            BotMessage.read_by_user.is_(False),
        )
    ) or 0


def user_messages(db: Session, actor: User, connection_id: int, since: str | None = None) -> list[dict]:
    row = _visible_connection(db, actor, connection_id)
    messages = _messages_since(db, row.id, since)
    for message in messages:
        if message.sender == "bot" and not message.read_by_user:
            message.read_by_user = True
    db.commit()
    return [_message_dict(message) for message in messages]


def user_reply(db: Session, actor: User, connection_id: int, text: str) -> dict:
    row = _visible_connection(db, actor, connection_id)
    if row.status != "approved":
        raise AppError("Approve this bot before chatting", 403)
    body = (text or "").strip()
    if not body:
        raise AppError("Write a message")
    message = BotMessage(connection_id=row.id, sender="user", body=body[:4000], cards=[], read_by_user=True)
    db.add(message)
    db.flush()
    _notify(row, message)
    db.commit()
    db.refresh(message)
    return _message_dict(message)


def bot_messages(db: Session, token: BotToken, since: str | None = None) -> list[dict]:
    row = _approved_connection(db, token)
    return [_message_dict(message) for message in _messages_since(db, row.id, since)]


def bot_reply(db: Session, token: BotToken, text: str, cards: list | None) -> dict:
    row = _approved_connection(db, token)
    body = (text or "").strip()
    parsed = _clean_cards(cards)
    if not body and not parsed:
        raise AppError("Send text or a card")
    message = BotMessage(connection_id=row.id, sender="bot", body=body[:4000], cards=parsed, read_by_user=False)
    db.add(message)
    db.commit()
    db.refresh(message)
    return _message_dict(message)


def _approved_connection(db: Session, token: BotToken) -> BotConnection:
    row = db.scalar(select(BotConnection).where(BotConnection.token_id == token.id))
    if row is None or row.status != "approved":
        raise AppError("This bot is not approved to chat", 403)
    return row


def _target_user(db: Session, email) -> User | None:
    if email in (None, ""):
        return None
    user = db.scalar(select(User).where(User.email == str(email).strip().lower()))
    if user is None or user.status != "approved":
        raise AppError("That LeadPilot user is not available", 404)
    return user


def _can_see(actor: User, row: BotConnection) -> bool:
    if actor.role in {"super_admin", "admin"}:
        return True
    return row.user_id == actor.id


def _can_decide(actor: User, row: BotConnection) -> bool:
    if actor.role in {"super_admin", "admin"}:
        return True
    return row.user_id == actor.id


def _visible_connection(db: Session, actor: User, connection_id: int) -> BotConnection:
    row = db.get(BotConnection, connection_id)
    if row is None or not _can_see(actor, row):
        raise AppError("Bot connection not found", 404)
    return row


def _messages_since(db: Session, connection_id: int, since: str | None) -> list[BotMessage]:
    rows = db.scalars(
        select(BotMessage).where(BotMessage.connection_id == connection_id).order_by(BotMessage.id.asc()).limit(200)
    ).all()
    if not since:
        return rows
    text = str(since).strip()
    if text.isdigit():
        cutoff = int(text)
        return [row for row in rows if row.id > cutoff]
    moment = _parse_time(text)
    return [row for row in rows if _aware(row.created_at) > moment]


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AppError("since must be a message id or an ISO timestamp") from exc
    return _aware(parsed)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _clean_cards(cards) -> list:
    if not cards:
        return []
    if not isinstance(cards, list):
        raise AppError("cards must be a list")
    cleaned = []
    for card in cards[:5]:
        if not isinstance(card, dict):
            continue
        kind = str(card.get("type") or "note")[:40]
        item = {"type": kind, "title": str(card.get("title") or "")[:200]}
        if kind == "leads":
            leads = []
            for lead in (card.get("leads") or [])[:20]:
                if isinstance(lead, dict) and str(lead.get("company") or "").strip():
                    leads.append({key: lead.get(key) for key in (
                        "company", "contact_name", "email", "phone", "website",
                        "city", "state", "country", "industry", "notes", "source_url",
                    )})
            item["leads"] = leads
        else:
            item["body"] = str(card.get("body") or "")[:2000]
        cleaned.append(item)
    return cleaned


def _notify(connection: BotConnection, message: BotMessage) -> None:
    url = (connection.webhook_url or "").strip()
    if not url:
        return
    headers = {"Content-Type": "application/json", "User-Agent": "LeadPilot/1.0"}
    secret = get_settings().grokbot_webhook_secret
    if secret:
        headers["X-LeadPilot-Webhook-Secret"] = secret
    payload = {
        "connection_id": connection.id,
        "message_id": message.id,
        "text": message.body,
        "sender": "user",
        "callback_base_url": get_settings().public_base_url.rstrip("/"),
    }
    try:
        with httpx.Client(timeout=8) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError:
        return


def _message_dict(message: BotMessage) -> dict:
    return {
        "id": message.id,
        "connection_id": message.connection_id,
        "sender": message.sender,
        "text": message.body,
        "cards": message.cards or [],
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def _user_view(db: Session, row: BotConnection, actor: User) -> dict:
    user = db.get(User, row.user_id) if row.user_id else None
    unread = db.scalar(
        select(func.count()).select_from(BotMessage).where(
            BotMessage.connection_id == row.id,
            BotMessage.sender == "bot",
            BotMessage.read_by_user.is_(False),
        )
    ) or 0
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description or "",
        "avatar_url": row.avatar_url or "",
        "status": row.status,
        "user_id": row.user_id,
        "user_email": user.email if user else "",
        "webhook_registered": bool(row.webhook_url),
        "unread": unread,
        "can_decide": _can_decide(actor, row),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _bot_view(db: Session, row: BotConnection) -> dict:
    user = db.get(User, row.user_id) if row.user_id else None
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description or "",
        "avatar_url": row.avatar_url or "",
        "webhook_url": row.webhook_url or "",
        "status": row.status,
        "user_email": user.email if user else "",
    }
