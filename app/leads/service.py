"""Lead persistence, status rules, and human review."""

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.errors import AppError
from app.models import LEAD_STATUSES, Comment, Lead, User
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
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
    }


def canonical_status(value: str | None) -> str:
    mapping = {status.lower(): status for status in LEAD_STATUSES}
    return mapping.get((value or "New").strip().lower(), "New")


def _owners(db: Session, leads: list[Lead]) -> dict:
    ids = {lead.owner_id for lead in leads if lead.owner_id}
    if not ids:
        return {}
    users = db.scalars(select(User).where(User.id.in_(ids))).all()
    return {user.id: user for user in users}


def list_leads(db: Session, status: str | None = None, query: str | None = None) -> list[dict]:
    statement = select(Lead).order_by(Lead.id.desc())
    if status:
        statement = statement.where(Lead.status == canonical_status(status))
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
        status = canonical_status(payload["status"])
        if status == "Qualified":
            raise AppError("Qualified status requires the human review step")
        if status not in LEAD_STATUSES:
            raise AppError("Unknown lead status")
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
    if "owner_id" in payload:
        lead.owner_id = payload["owner_id"]
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
