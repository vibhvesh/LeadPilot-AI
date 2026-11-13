"""Lead list, edits, and the human review step."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_module
from app.leads.service import create_lead, get_lead_or_404, lead_dict, list_leads, review_lead, update_lead

router = APIRouter(prefix="/api/leads")


@router.get("")
def get_leads(status: str | None = None, q: str | None = None, db: Session = Depends(get_db), _user=Depends(require_module("leads"))):
    return list_leads(db, status=status, query=q)


@router.post("")
def post_lead(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("leads", manage=True))):
    return create_lead(db, actor, body)


@router.get("/{lead_id}")
def get_lead(lead_id: int, db: Session = Depends(get_db), _user=Depends(require_module("leads"))):
    return lead_dict(get_lead_or_404(db, lead_id))


@router.patch("/{lead_id}")
def patch_lead(lead_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("leads", manage=True))):
    return update_lead(db, actor, lead_id, body)


@router.post("/{lead_id}/review")
def post_review(lead_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("leads", manage=True))):
    return review_lead(db, actor, lead_id, str(body.get("decision") or ""), str(body.get("note") or ""))
