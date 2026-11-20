"""Lead list, assignment, status, close, and the human review step."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_module
from app.leads.service import (
    active_users,
    bulk_assign,
    bulk_status,
    close_lead,
    create_lead,
    get_lead_or_404,
    lead_dict,
    list_leads,
    reopen_lead,
    review_lead,
    update_lead,
    _owners,
)

router = APIRouter(prefix="/api/leads")


@router.get("")
def get_leads(
    status: str | None = None,
    q: str | None = None,
    owner_id: int | None = None,
    mine: bool = False,
    show_closed: bool = False,
    contact_type: str | None = None,
    db: Session = Depends(get_db),
    actor=Depends(require_module("leads")),
):
    return list_leads(
        db,
        status=status,
        query=q,
        owner_id=owner_id,
        mine=mine,
        actor=actor,
        show_closed=show_closed,
        contact_type=contact_type,
    )


@router.get("/assignees")
def get_assignees(db: Session = Depends(get_db), _user=Depends(require_module("leads"))):
    return {"users": active_users(db)}


@router.post("/bulk-assign")
def post_bulk_assign(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("leads"))):
    return bulk_assign(db, actor, list(body.get("ids") or []), int(body.get("owner_id") or 0))


@router.post("/bulk-status")
def post_bulk_status(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("leads"))):
    return bulk_status(db, actor, list(body.get("ids") or []), str(body.get("status") or ""), str(body.get("reason") or ""))


@router.post("")
def post_lead(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("leads", manage=True))):
    return create_lead(db, actor, body)


@router.get("/{lead_id}")
def get_lead(lead_id: int, db: Session = Depends(get_db), _user=Depends(require_module("leads"))):
    lead = get_lead_or_404(db, lead_id)
    return lead_dict(lead, _owners(db, [lead]))


@router.patch("/{lead_id}")
def patch_lead(lead_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("leads", manage=True))):
    return update_lead(db, actor, lead_id, body)


@router.post("/{lead_id}/close")
def post_close(lead_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("leads"))):
    return close_lead(db, actor, lead_id, str(body.get("outcome") or ""), str(body.get("reason") or ""))


@router.post("/{lead_id}/reopen")
def post_reopen(lead_id: int, db: Session = Depends(get_db), actor=Depends(require_module("leads"))):
    return reopen_lead(db, actor, lead_id)


@router.post("/{lead_id}/review")
def post_review(lead_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("leads", manage=True))):
    return review_lead(db, actor, lead_id, str(body.get("decision") or ""), str(body.get("note") or ""))
