"""Deep-search requests created in the app and completed by Grok Bot."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai_search.planner import make_plan
from app.audit.service import record
from app.bot.webhook import dispatch
from app.core.config import get_settings
from app.core.errors import AppError
from app.leads.service import ingest_lead
from app.models import BotToken, DeepSearchRequest, Lead, User
from app.models.identity import utcnow
from app.settings.profile import load_profile


def create_request(db: Session, actor, text: str) -> dict:
    body = (text or "").strip()
    if len(body) < 3:
        raise AppError("Describe the deep search")
    plan = make_plan(db, actor, body, load_profile(db))
    row = DeepSearchRequest(user_id=actor.id, text=body, plan=plan, status="pending")
    db.add(row)
    db.flush()
    payload = {
        "request_id": row.id,
        "text": row.text,
        "plan": plan,
        "callback_base_url": get_settings().public_base_url.rstrip("/"),
    }
    status, error = dispatch(payload)
    row.webhook_status = status
    row.webhook_error = error[:200]
    record(
        db,
        user=actor,
        action="deep_search_request",
        module="search",
        target=str(row.id),
        detail={"webhook": status, "queries": plan.get("queries")},
    )
    db.commit()
    db.refresh(row)
    return serialize_request(db, row)


def list_requests(db: Session, status: str | None = None) -> list[dict]:
    statement = select(DeepSearchRequest).order_by(DeepSearchRequest.id.desc()).limit(50)
    if status:
        statement = statement.where(DeepSearchRequest.status == status)
    return [serialize_request(db, row) for row in db.scalars(statement).all()]


def claim_request(db: Session, token: BotToken, request_id: int) -> dict:
    row = _get(db, request_id)
    if row.status == "completed":
        raise AppError("This request is already complete", 409)
    if row.status == "claimed" and row.claimed_token_id not in (None, token.id):
        raise AppError("This request is already claimed", 409)
    row.status = "claimed"
    row.claimed_token_id = token.id
    record(db, action="deep_search_claim", module="grokbot", target=str(row.id), detail={"token_id": token.id}, email=f"bot:{token.name}")
    db.commit()
    db.refresh(row)
    return serialize_request(db, row)


def complete_request(db: Session, token: BotToken, request_id: int, notes: str) -> dict:
    row = _get(db, request_id)
    if row.status == "completed":
        raise AppError("This request is already complete", 409)
    row.status = "completed"
    row.notes = (notes or "").strip()[:4000]
    row.completed_at = utcnow()
    if row.claimed_token_id is None:
        row.claimed_token_id = token.id
    record(db, action="deep_search_complete", module="grokbot", target=str(row.id), detail={"token_id": token.id}, email=f"bot:{token.name}")
    db.commit()
    db.refresh(row)
    return serialize_request(db, row)


def add_leads(db: Session, token: BotToken, request_id: int, leads: list) -> dict:
    row = _get(db, request_id)
    if not isinstance(leads, list) or not leads:
        raise AppError("Send at least one lead")
    if len(leads) > 50:
        raise AppError("Send at most 50 leads at a time")
    actor = db.get(User, row.user_id)
    if actor is None:
        raise AppError("The person who asked for this search is no longer available", 400)
    created = 0
    duplicates = 0
    skipped = 0
    for item in leads:
        if not isinstance(item, dict):
            skipped += 1
            continue
        outcome = ingest_lead(db, actor, item, source="grokbot", request_id=row.id)
        if outcome == "created":
            created += 1
        elif outcome == "duplicate":
            duplicates += 1
        else:
            skipped += 1
    record(
        db,
        user=actor,
        action="grokbot_leads",
        module="grokbot",
        target=str(row.id),
        detail={"created": created, "duplicates": duplicates, "skipped": skipped, "token_id": token.id},
    )
    db.commit()
    return {"request_id": row.id, "created": created, "duplicates": duplicates, "skipped": skipped}


def serialize_request(db: Session, row: DeepSearchRequest) -> dict:
    lead_count = db.scalar(select(func.count()).select_from(Lead).where(Lead.deep_search_request_id == row.id)) or 0
    return {
        "id": row.id,
        "text": row.text,
        "plan": row.plan or {},
        "status": row.status,
        "notes": row.notes or "",
        "webhook_status": row.webhook_status,
        "lead_count": lead_count,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def _get(db: Session, request_id: int) -> DeepSearchRequest:
    row = db.get(DeepSearchRequest, request_id)
    if row is None:
        raise AppError("Deep search request not found", 404)
    return row
