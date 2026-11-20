"""Lead persistence, status rules, and human review."""

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.errors import AppError
from app.models import CLOSED_STATUSES, LEAD_STATUSES, Comment, Lead, LeadActivity, User
from app.models.identity import utcnow
from app.search.normalize import dedup_key


def region_label(lead: Lead) -> str:
    parts = [lead.city or "", lead.state or "", lead.country or ""]
    return ", ".join(part for part in parts if part)


def lead_dict(lead: Lead, owners: dict | None = None) -> dict:
    owner = None
    if owners is not None:
        owner = owners.get(lead.owner_id)
    return {
        "id": lead.id,
        "company": lead.company,
        "contact_name": lead.contact_name or "",
        "email": lead.email or "",
        "phone": lead.phone or "",
        "website": lead.website or "",
        "source": lead.source or "",
        "source_url": lead.source_url or "",
        "country": lead.country or "",
        "state": lead.state or "",
        "district": lead.district or "",
        "city": lead.city or "",
        "postal_code": lead.postal_code or "",
        "region": region_label(lead),
        "industry": lead.industry or "",
        "company_size": lead.company_size or "",
        "keywords": lead.keywords or "",
        "status": canonical_status(lead.status),
        "score": lead.score,
        "estimated_value": lead.estimated_value or 0,
        "notes": lead.notes or "",
        "why_fit": lead.why_fit or "",
        "qualification_summary": lead.qualification_summary or "",
        "deep_search_request_id": lead.deep_search_request_id,
        "human_reviewed": bool(lead.human_reviewed),
        "reviewed_by": lead.reviewed_by,
        "owner_id": lead.owner_id,
        "owner_name": owner.display_name if owner else "",
        "contact_type": lead.contact_type or "",
        "close_reason": lead.close_reason or "",
        "closed_at": lead.closed_at.isoformat() if lead.closed_at else None,
        "closed": (lead.status or "") in CLOSED_STATUSES,
        "pending_owner_id": lead.pending_owner_id,
        "pending_owner_name": owners.get(lead.pending_owner_id).display_name if owners and owners.get(lead.pending_owner_id) else "",
        "in_review": lead.status == "In review",
        "review_outcome": lead.review_outcome or "",
        "review_reason": lead.review_reason or "",
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
    }


def canonical_status(value: str | None) -> str:
    mapping = {status.lower(): status for status in LEAD_STATUSES}
    return mapping.get((value or "New").strip().lower(), "New")


def _owners(db: Session, leads: list[Lead]) -> dict:
    ids = set()
    for lead in leads:
        if lead.owner_id:
            ids.add(lead.owner_id)
        if lead.pending_owner_id:
            ids.add(lead.pending_owner_id)
    if not ids:
        return {}
    users = db.scalars(select(User).where(User.id.in_(ids))).all()
    return {user.id: user for user in users}


def is_manager(user: User) -> bool:
    return user.role in {"admin", "super_admin"}


def _actor_name(user: User) -> str:
    return user.display_name or user.email


def log_activity(db: Session, lead: Lead, actor: User, action: str, summary: str) -> None:
    db.add(LeadActivity(lead_id=lead.id, actor_id=actor.id, action=action, summary=summary[:400]))


def can_touch(actor: User, lead: Lead) -> bool:
    if is_manager(actor):
        return True
    return lead.owner_id is None or lead.owner_id == actor.id


def active_users(db: Session) -> list[dict]:
    rows = db.scalars(select(User).where(User.status == "approved").order_by(User.display_name, User.email)).all()
    return [{"id": row.id, "name": row.display_name or row.email, "email": row.email, "role": row.role} for row in rows]


def list_leads(
    db: Session,
    status: str | None = None,
    query: str | None = None,
    owner_id: int | None = None,
    mine: bool = False,
    actor: User | None = None,
    show_closed: bool = False,
    contact_type: str | None = None,
    awaiting_review: bool = False,
    pending_for_me: bool = False,
) -> list[dict]:
    statement = select(Lead).order_by(Lead.id.desc())
    if awaiting_review:
        statement = statement.where(Lead.status == "In review")
    if pending_for_me and actor is not None:
        statement = statement.where(Lead.pending_owner_id == actor.id)
    if mine and actor is not None:
        statement = statement.where(Lead.owner_id == actor.id)
    elif owner_id:
        statement = statement.where(Lead.owner_id == owner_id)
    if contact_type:
        statement = statement.where(Lead.contact_type == contact_type.strip())
    if status:
        statement = statement.where(Lead.status == canonical_status(status))
    elif not show_closed:
        statement = statement.where(Lead.status.notin_(CLOSED_STATUSES))
    if query:
        like = f"%{query.strip()}%"
        statement = statement.where(
            or_(
                Lead.company.ilike(like),
                Lead.contact_name.ilike(like),
                Lead.email.ilike(like),
                Lead.city.ilike(like),
                Lead.industry.ilike(like),
            )
        )
    leads = db.scalars(statement).all()
    owners = _owners(db, leads)
    rows = [lead_dict(lead, owners) for lead in leads]
    from app.outreach.service import latest_labels

    labels = latest_labels(db, [row["id"] for row in rows])
    for row in rows:
        row["contacted_badge"] = labels.get(row["id"], "")
    return rows


def get_lead_or_404(db: Session, lead_id: int) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise AppError("Lead not found", 404)
    return lead


def create_lead(db: Session, actor: User, payload: dict) -> dict:
    company = (payload.get("company") or "").strip()
    if len(company) < 2:
        raise AppError("Company name is required")
    website = (payload.get("website") or "").strip()
    key = dedup_key(company, website)
    existing = db.scalar(select(Lead).where(Lead.dedup_key == key))
    if existing is not None:
        raise AppError("A lead for this company already exists", 409)
    email = (payload.get("email") or "").strip().lower()
    if email:
        by_email = db.scalar(select(Lead).where(Lead.email.ilike(email)))
        if by_email is not None:
            raise AppError(f"A lead for {email} already exists ({by_email.company})", 409)
    contact_type = (payload.get("contact_type") or "").strip()
    tags = payload.get("tags") or []
    if not contact_type and isinstance(tags, list) and "linkedin_dm" in tags:
        contact_type = "linkedin_dm"
    status = canonical_status(payload.get("status") or "New")
    if status == "Qualified":
        raise AppError("Qualified status requires human review")
    lead = Lead(
        company=company,
        contact_name=(payload.get("contact_name") or "").strip(),
        email=(payload.get("email") or "").strip(),
        phone=(payload.get("phone") or "").strip(),
        website=website,
        source=(payload.get("source") or "manual").strip() or "manual",
        source_url=(payload.get("source_url") or "").strip(),
        country=(payload.get("country") or "").strip(),
        state=(payload.get("state") or "").strip(),
        district=(payload.get("district") or "").strip(),
        city=(payload.get("city") or "").strip(),
        postal_code=(payload.get("postal_code") or "").strip(),
        industry=(payload.get("industry") or "").strip(),
        company_size=(payload.get("company_size") or "").strip(),
        keywords=(payload.get("keywords") or "").strip(),
        status=status,
        estimated_value=int(payload.get("estimated_value") or 0),
        notes=(payload.get("notes") or "").strip(),
        contact_type=contact_type,
        owner_id=payload.get("owner_id") or actor.id,
        created_by=actor.id,
        dedup_key=key,
        raw_payload={"origin": "manual"},
    )
    db.add(lead)
    db.flush()
    record(db, user=actor, action="lead_create", module="leads", target=str(lead.id), detail={"company": lead.company})
    db.commit()
    db.refresh(lead)
    return lead_dict(lead, _owners(db, [lead]))


def update_lead(db: Session, actor: User, lead_id: int, payload: dict) -> dict:
    lead = get_lead_or_404(db, lead_id)
    if "status" in payload and payload["status"] is not None:
        if not can_touch(actor, lead):
            raise AppError("You can only change leads you own or leads nobody owns", 403)
        status = canonical_status(payload["status"])
        if status == "Qualified":
            raise AppError("Qualified status requires the human review step")
        if status == "In review":
            raise AppError("Submit a close request instead")
        if status in CLOSED_STATUSES and not is_manager(actor):
            raise AppError("Only an admin can close a lead", 403)
        if status not in LEAD_STATUSES:
            raise AppError("Unknown lead status")
        if status != lead.status:
            log_activity(db, lead, actor, "status", f"{_actor_name(actor)} moved the lead to {status}")
        lead.status = status
    for field in (
        "contact_name",
        "email",
        "phone",
        "website",
        "country",
        "state",
        "district",
        "city",
        "postal_code",
        "industry",
        "company_size",
        "keywords",
        "notes",
        "source",
    ):
        if field in payload and payload[field] is not None:
            setattr(lead, field, str(payload[field]).strip())
    if "estimated_value" in payload and payload["estimated_value"] is not None:
        lead.estimated_value = int(payload["estimated_value"])
    if "owner_id" in payload and payload["owner_id"]:
        assign_lead(db, actor, lead, int(payload["owner_id"]), commit=False)
    if "company" in payload and payload["company"]:
        lead.company = payload["company"].strip()
    lead.dedup_key = dedup_key(lead.company, lead.website or "")
    record(db, user=actor, action="lead_update", module="leads", target=str(lead.id), detail={"status": lead.status})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError("Another lead already uses this company or website", 409) from exc
    db.refresh(lead)
    return lead_dict(lead, _owners(db, [lead]))


def review_lead(db: Session, actor: User, lead_id: int, decision: str, note: str = "") -> dict:
    lead = get_lead_or_404(db, lead_id)
    decision = decision.strip().lower()
    if decision not in {"qualify", "reject", "hold"}:
        raise AppError("Decision must be qualify, reject, or hold")
    if decision == "qualify":
        lead.status = "Qualified"
    elif decision == "reject":
        lead.status = "Lost"
    lead.human_reviewed = True
    lead.reviewed_by = actor.email
    lead.reviewed_at = utcnow()
    if note.strip():
        db.add(Comment(author_id=actor.id, lead_id=lead.id, body=note.strip()))
        lead.notes = (lead.notes + "\n" + note.strip()).strip()
    record(
        db,
        user=actor,
        action="human_review",
        module="leads",
        target=str(lead.id),
        detail={"decision": decision, "status": lead.status},
    )
    db.commit()
    db.refresh(lead)
    return lead_dict(lead, _owners(db, [lead]))


def ingest_lead(db: Session, actor: User, data: dict, *, source: str, request_id: int | None = None, min_score: int | None = None) -> str:
    """Deduplicate, enrich, and score one lead. The caller commits."""
    company = str(data.get("company") or "").strip()
    if len(company) < 2:
        return "skipped"
    website = str(data.get("website") or "").strip()
    key = dedup_key(company, website)
    if db.scalar(select(Lead.id).where(Lead.dedup_key == key)):
        return "duplicate"
    why = str(data.get("why_fit") or "").strip()
    lead = Lead(
        company=company[:250],
        contact_name=str(data.get("contact_name") or "").strip()[:250],
        email=str(data.get("email") or "").strip()[:320],
        phone=str(data.get("phone") or "").strip()[:80],
        website=website[:500],
        source=(source or "manual")[:80],
        source_url=str(data.get("source_url") or "").strip()[:1000],
        country=str(data.get("country") or "").strip()[:80],
        state=str(data.get("state") or "").strip()[:80],
        district=str(data.get("district") or "").strip()[:80],
        city=str(data.get("city") or "").strip()[:80],
        postal_code=str(data.get("postal_code") or "").strip()[:20],
        industry=str(data.get("industry") or "").strip()[:120],
        company_size=str(data.get("company_size") or "").strip()[:40],
        keywords=str(data.get("keywords") or "").strip()[:500],
        status="New",
        contact_type=_contact_type(data),
        estimated_value=int(data.get("estimated_value") or 0),
        notes=str(data.get("notes") or data.get("snippet") or "").strip(),
        why_fit=why,
        owner_id=getattr(actor, "id", None),
        created_by=getattr(actor, "id", None),
        dedup_key=key,
        deep_search_request_id=request_id,
        raw_payload={"snippet": str(data.get("snippet") or "")[:1000], "origin": source},
    )
    try:
        with db.begin_nested():
            db.add(lead)
            db.flush()
    except IntegrityError:
        return "duplicate"
    from app.agents.scoring import apply_score
    from app.agents.steps import enrich

    enrich(db, lead)
    apply_score(db, actor, lead)
    if min_score is not None and lead.score is not None and lead.score < min_score:
        db.delete(lead)
        return "below_score"
    return "created"


def _contact_type(payload: dict) -> str:
    contact_type = str(payload.get("contact_type") or "").strip()
    tags = payload.get("tags") or []
    if not contact_type and isinstance(tags, list) and "linkedin_dm" in tags:
        return "linkedin_dm"
    return contact_type[:40]


def _require_touch(actor: User, lead: Lead) -> None:
    if not can_touch(actor, lead):
        raise AppError("You can only change leads you own or leads nobody owns", 403)


def assign_lead(db: Session, actor: User, lead: Lead, owner_id: int, commit: bool = True) -> dict:
    _require_touch(actor, lead)
    person = db.get(User, owner_id)
    if person is None or person.status != "approved":
        raise AppError("That person is not an active user", 404)
    if actor.id == person.id:
        lead.owner_id = person.id
        lead.pending_owner_id = None
        lead.pending_from_id = None
        log_activity(db, lead, actor, "assign", f"{_actor_name(actor)} took the lead")
    elif lead.pending_owner_id != person.id:
        lead.pending_owner_id = person.id
        lead.pending_from_id = lead.owner_id or actor.id
        log_activity(db, lead, actor, "transfer_offered", f"{_actor_name(actor)} offered the lead to {_actor_name(person)}")
    if commit:
        db.commit()
        db.refresh(lead)
    return lead_dict(lead, _owners(db, [lead]))


def bulk_assign(db: Session, actor: User, ids: list[int], owner_id: int) -> dict:
    if not ids:
        raise AppError("Choose at least one lead", 400)
    for lead_id in ids:
        assign_lead(db, actor, get_lead_or_404(db, int(lead_id)), int(owner_id), commit=False)
    db.commit()
    return {"updated": len(ids)}


def bulk_status(db: Session, actor: User, ids: list[int], status: str, reason: str = "") -> dict:
    if not ids:
        raise AppError("Choose at least one lead", 400)
    status = canonical_status(status)
    if status not in LEAD_STATUSES or status == "Qualified":
        raise AppError("Unknown lead status")
    note = (reason or "").strip()
    if status in CLOSED_STATUSES and not is_manager(actor):
        raise AppError("Only an admin can close a lead", 403)
    if status in CLOSED_STATUSES and len(note) < 3:
        raise AppError("A short reason is required to close leads", 400)
    for lead_id in ids:
        lead = get_lead_or_404(db, int(lead_id))
        _require_touch(actor, lead)
        if lead.status == status:
            continue
        lead.status = status
        if status in CLOSED_STATUSES:
            lead.close_reason = note[:500]
            lead.closed_at = utcnow()
            log_activity(db, lead, actor, "close", f"{_actor_name(actor)} closed the lead as {status}: {note[:180]}")
        else:
            log_activity(db, lead, actor, "status", f"{_actor_name(actor)} moved the lead to {status}")
    db.commit()
    return {"updated": len(ids)}


_CLOSE_OUTCOMES = {"won": "Won", "lost": "Lost", "not_a_fit": "Not a fit", "not a fit": "Not a fit"}


def close_lead(db: Session, actor: User, lead_id: int, outcome: str, reason: str) -> dict:
    if not is_manager(actor):
        raise AppError("Only an admin can close a lead", 403)
    lead = get_lead_or_404(db, lead_id)
    status = _CLOSE_OUTCOMES.get((outcome or "").strip().lower())
    if status is None:
        raise AppError("Close as won, lost, or not_a_fit", 400)
    note = (reason or "").strip()
    if len(note) < 3:
        raise AppError("A short reason is required", 400)
    lead.status = status
    lead.close_reason = note[:500]
    lead.closed_at = utcnow()
    lead.review_outcome = ""
    lead.review_reason = ""
    lead.review_from_status = ""
    log_activity(db, lead, actor, "close", f"{_actor_name(actor)} closed the lead as {status}: {note[:180]}")
    db.commit()
    db.refresh(lead)
    return lead_dict(lead, _owners(db, [lead]))


def reopen_lead(db: Session, actor: User, lead_id: int) -> dict:
    if not is_manager(actor):
        raise AppError("Only an admin can reopen a lead", 403)
    lead = get_lead_or_404(db, lead_id)
    if lead.status not in CLOSED_STATUSES and lead.closed_at is None:
        raise AppError("This lead is already open", 400)
    lead.status = "Contacted"
    lead.close_reason = ""
    lead.closed_at = None
    log_activity(db, lead, actor, "reopen", f"{_actor_name(actor)} reopened the lead")
    db.commit()
    db.refresh(lead)
    return lead_dict(lead, _owners(db, [lead]))


def accept_transfer(db: Session, actor: User, lead_id: int) -> dict:
    lead = get_lead_or_404(db, lead_id)
    if lead.pending_owner_id != actor.id:
        raise AppError("This transfer is not waiting on you", 403)
    lead.owner_id = actor.id
    lead.pending_owner_id = None
    lead.pending_from_id = None
    log_activity(db, lead, actor, "transfer_accepted", f"{_actor_name(actor)} accepted the lead")
    db.commit()
    db.refresh(lead)
    return lead_dict(lead, _owners(db, [lead]))


def decline_transfer(db: Session, actor: User, lead_id: int, reason: str) -> dict:
    lead = get_lead_or_404(db, lead_id)
    if lead.pending_owner_id != actor.id:
        raise AppError("This transfer is not waiting on you", 403)
    note = (reason or "").strip()
    if len(note) < 3:
        raise AppError("A short reason is required", 400)
    lead.owner_id = lead.pending_from_id
    lead.pending_owner_id = None
    lead.pending_from_id = None
    log_activity(db, lead, actor, "transfer_declined", f"{_actor_name(actor)} declined the lead: {note[:180]}")
    db.commit()
    db.refresh(lead)
    return lead_dict(lead, _owners(db, [lead]))


def request_close(db: Session, actor: User, lead_id: int, outcome: str, reason: str) -> dict:
    if is_manager(actor):
        raise AppError("Admins close leads directly", 400)
    lead = get_lead_or_404(db, lead_id)
    _require_touch(actor, lead)
    if lead.status in CLOSED_STATUSES:
        raise AppError("This lead is already closed", 400)
    if lead.status == "In review":
        raise AppError("This lead is already awaiting review", 400)
    status = _CLOSE_OUTCOMES.get((outcome or "").strip().lower())
    if status is None:
        raise AppError("Request won, lost, or not_a_fit", 400)
    note = (reason or "").strip()
    if len(note) < 3:
        raise AppError("A short reason is required", 400)
    lead.review_from_status = lead.status
    lead.review_outcome = status
    lead.review_reason = note[:500]
    lead.status = "In review"
    log_activity(db, lead, actor, "request_close", f"{_actor_name(actor)} asked to close the lead as {status}: {note[:180]}")
    db.commit()
    db.refresh(lead)
    return lead_dict(lead, _owners(db, [lead]))


def decide_review(db: Session, actor: User, lead_id: int, decision: str, comment: str = "") -> dict:
    if not is_manager(actor):
        raise AppError("Only an admin can review a close request", 403)
    lead = get_lead_or_404(db, lead_id)
    if lead.status != "In review":
        raise AppError("This lead is not awaiting review", 400)
    choice = (decision or "").strip().lower()
    if choice == "approve":
        lead.status = lead.review_outcome or "Lost"
        lead.close_reason = lead.review_reason or ""
        lead.closed_at = utcnow()
        lead.review_outcome = ""
        lead.review_reason = ""
        lead.review_from_status = ""
        log_activity(db, lead, actor, "approve_close", f"{_actor_name(actor)} approved the close as {lead.status}")
    elif choice == "reject":
        note = (comment or "").strip()
        if len(note) < 3:
            raise AppError("Tell the owner why this stays open", 400)
        previous = lead.review_from_status or "Contacted"
        lead.status = previous if previous not in CLOSED_STATUSES else "Contacted"
        lead.review_outcome = ""
        lead.review_reason = ""
        lead.review_from_status = ""
        db.add(Comment(author_id=actor.id, lead_id=lead.id, body=note[:4000]))
        log_activity(db, lead, actor, "reject_close", f"{_actor_name(actor)} sent the lead back: {note[:180]}")
    else:
        raise AppError("Approve or reject the close request", 400)
    db.commit()
    db.refresh(lead)
    return lead_dict(lead, _owners(db, [lead]))


def queue_counts(db: Session, actor: User) -> dict:
    from sqlalchemy import func

    review = db.scalar(select(func.count()).select_from(Lead).where(Lead.status == "In review")) or 0
    pending = db.scalar(select(func.count()).select_from(Lead).where(Lead.pending_owner_id == actor.id)) or 0
    return {"awaiting_review": int(review), "pending_for_me": int(pending)}
