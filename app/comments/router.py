"""Workspace announcements and lead comments."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.database import get_db
from app.core.deps import require_module
from app.core.errors import AppError
from app.models import Comment, Lead, User

router = APIRouter(prefix="/api")


def _dict(row: Comment, author: User | None) -> dict:
    return {
        "id": row.id,
        "lead_id": row.lead_id,
        "body": row.body,
        "author_name": author.display_name if author else "",
        "author_email": author.email if author else "",
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/comments")
def list_comments(lead_id: int | None = None, db: Session = Depends(get_db), _user=Depends(require_module("comments"))):
    statement = select(Comment).order_by(Comment.id.desc()).limit(100)
    if lead_id is None:
        statement = statement.where(Comment.lead_id.is_(None))
    else:
        statement = statement.where(Comment.lead_id == lead_id)
    rows = db.scalars(statement).all()
    return [_hydrate(db, row) for row in rows]


@router.post("/comments")
def post_comment(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("comments", manage=True))):
    text = str(body.get("body") or "").strip()
    if not text:
        raise AppError("Write a comment before posting")
    lead_id = body.get("lead_id")
    if lead_id and db.get(Lead, int(lead_id)) is None:
        raise AppError("Lead not found", 404)
    row = Comment(author_id=actor.id, lead_id=int(lead_id) if lead_id else None, body=text[:4000])
    db.add(row)
    db.flush()
    record(db, user=actor, action="comment", module="comments", target=str(row.id), detail={"lead_id": row.lead_id})
    db.commit()
    db.refresh(row)
    return _hydrate(db, row)


def _hydrate(db: Session, row: Comment) -> dict:
    return _dict(row, db.get(User, row.author_id))
