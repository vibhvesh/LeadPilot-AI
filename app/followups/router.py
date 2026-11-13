"""Reminders attached to the workspace or to a lead."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import nulls_last, select
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.database import get_db
from app.core.deps import require_module
from app.core.errors import AppError
from app.models import FollowUp, Lead, User

router = APIRouter(prefix="/api/followups")


def _parse_due(value):
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise AppError("Enter a valid due date") from exc
    return parsed


def _dict(row: FollowUp, lead: Lead | None, owner: User | None) -> dict:
    return {
        "id": row.id,
        "lead_id": row.lead_id,
        "company": lead.company if lead else "",
        "title": row.title,
        "notes": row.notes or "",
        "due_at": row.due_at.isoformat() if row.due_at else None,
        "status": row.status,
        "owner_name": owner.display_name if owner else "",
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("")
def list_followups(db: Session = Depends(get_db), _user=Depends(require_module("followups"))):
    rows = db.scalars(select(FollowUp).order_by(nulls_last(FollowUp.due_at.asc()), FollowUp.id.desc())).all()
    return [_hydrate(db, row) for row in rows]


@router.post("")
def create_followup(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("followups", manage=True))):
    title = str(body.get("title") or "").strip()
    if len(title) < 2:
        raise AppError("Follow-up title is required")
    lead_id = body.get("lead_id")
    if lead_id:
        if db.get(Lead, int(lead_id)) is None:
            raise AppError("Lead not found", 404)
    row = FollowUp(
        lead_id=int(lead_id) if lead_id else None,
        user_id=actor.id,
        title=title[:300],
        notes=str(body.get("notes") or "").strip(),
        due_at=_parse_due(body.get("due_at")),
        status="open",
    )
    db.add(row)
    db.flush()
    record(db, user=actor, action="followup_create", module="followups", target=str(row.id), detail={"title": row.title})
    db.commit()
    db.refresh(row)
    return _hydrate(db, row)


@router.patch("/{followup_id}")
def patch_followup(followup_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("followups", manage=True))):
    row = db.get(FollowUp, followup_id)
    if row is None:
        raise AppError("Follow-up not found", 404)
    if "status" in body:
        status = str(body["status"])
        if status not in {"open", "done"}:
            raise AppError("Status must be open or done")
        row.status = status
    if "title" in body and body["title"]:
        row.title = str(body["title"]).strip()[:300]
    if "notes" in body:
        row.notes = str(body["notes"] or "")
    if "due_at" in body:
        row.due_at = _parse_due(body.get("due_at"))
    db.commit()
    db.refresh(row)
    return _hydrate(db, row)


def _hydrate(db: Session, row: FollowUp) -> dict:
    lead = db.get(Lead, row.lead_id) if row.lead_id else None
    owner = db.get(User, row.user_id)
    return _dict(row, lead, owner)
