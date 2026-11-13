"""User activity monitor."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_module
from app.dashboard.service import activity_summary
from app.models import AuditEvent

router = APIRouter(prefix="/api/activity")


@router.get("/summary")
def summary(db: Session = Depends(get_db), _user=Depends(require_module("activity"))):
    return activity_summary(db)


@router.get("")
def events(db: Session = Depends(get_db), _user=Depends(require_module("activity"))):
    rows = db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(80)).all()
    return [
        {
            "id": row.id,
            "email": row.email,
            "action": row.action,
            "module": row.module,
            "target": row.target,
            "success": row.success,
            "detail": row.detail or {},
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
