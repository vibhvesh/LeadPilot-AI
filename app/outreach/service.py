"""Record outreach, block a second first touch, and list what is due today."""

from datetime import timedelta
from urllib.parse import quote

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import FollowUp, Lead, User
from app.models.identity import utcnow
from app.models.outreach import TEMPLATE_KEYS, LeadEvent, OutreachMessage, OutreachTemplate
from app.models.workspace import WorkspaceSettings
from app.outreach.gmail import send_gmail
from app.outreach.templates import ensure_templates, fields_for, render

ORDER = {"first": 0, "followup_1": 1, "followup_2": 2}
NEXT = {"first": "followup_1", "followup_1": "followup_2", "followup_2": None}


def _stamp(value) -> str:
    if value is None:
        return ""
    return value.strftime("%d %b").lstrip("0")


def team_bcc(db: Session) -> str:
    row = db.get(WorkspaceSettings, 1)
    return (row.team_bcc or "").strip() if row is not None else ""


def set_team_bcc(db: Session, value: str) -> str:
    row = db.get(WorkspaceSettings, 1)
    if row is None:
        row = WorkspaceSettings(id=1)
        db.add(row)
        db.flush()
    row.team_bcc = (value or "").strip()[:500]
    db.commit()
    return row.team_bcc


def history(db: Session, lead: Lead) -> list[OutreachMessage]:
    email = (lead.email or "").strip().lower()
    filters = [OutreachMessage.lead_id == lead.id]
    if email:
        filters.append(OutreachMessage.to_email == email)
    return list(db.scalars(select(OutreachMessage).where(or_(*filters)).order_by(OutreachMessage.id.asc())).all())


def next_key(rows: list[OutreachMessage]) -> str | None:
    sent = {row.template_key for row in rows}
    for key in TEMPLATE_KEYS:
        if key not in sent:
            return key
    return None


def guard(actor: User, rows: list[OutreachMessage], key: str, reason: str) -> None:
    if key not in TEMPLATE_KEYS:
        raise AppError("Unknown template")
    expected = next_key(rows)
    if expected is None:
        if actor.role not in {"admin", "super_admin"} or not reason.strip():
            raise AppError("The sequence is already complete. An admin can override with a reason.", 409)
        return
    if key != expected:
        prior = next((row for row in rows if row.template_key == "first"), rows[-1] if rows else None)
        when = _stamp(prior.sent_at) if prior is not None else ""
        admin = actor.role in {"admin", "super_admin"} and reason.strip()
        if not admin and key == "first" and any(row.template_key == "first" for row in rows):
            raise AppError(f"First outreach was already sent{(' on ' + when) if when else ''}. Use the next follow-up.", 409)
        if not admin:
            raise AppError("That step is not next. An admin can override with a reason.", 409)


def mailto_link(to: str, subject: str, body: str, bcc: str) -> str:
    return f"mailto:{quote(to)}?subject={quote(subject)}&body={quote(body)}&bcc={quote(bcc)}"


def preview(db: Session, actor: User, lead: Lead, key: str) -> dict:
    ensure_templates(db)
    row = db.scalar(select(OutreachTemplate).where(OutreachTemplate.key == key))
    if row is None:
        raise AppError("Unknown template")
    data = fields_for(lead, actor)
    subject = render(row.subject, data)
    body = render(row.body, data)
    rows = history(db, lead)
    blocked = None
    try:
        guard(actor, rows, key, "")
    except AppError as exc:
        blocked = exc.message
    return {
        "template_key": key,
        "name": row.name,
        "subject": subject,
        "body": body,
        "next_key": next_key(rows),
        "blocked": blocked,
        "mailto": mailto_link(lead.email or "", subject, body, team_bcc(db)),
        "gmail_connected": bool(getattr(actor, "gmail_refresh_token", "")),
        "history": [_public(db, item) for item in rows],
    }


def _public(db: Session, row: OutreachMessage) -> dict:
    user = db.get(User, row.user_id)
    return {
        "id": row.id,
        "template_key": row.template_key,
        "channel": row.channel,
        "sender_name": user.display_name if user else "",
        "sent_at": row.sent_at.isoformat() if row.sent_at else None,
        "sent_label": _stamp(row.sent_at),
        "to_email": row.to_email,
    }


def record_send(db: Session, actor: User, lead: Lead, *, key: str, channel: str, subject: str, body: str, days: int, reason: str) -> dict:
    rows = history(db, lead)
    guard(actor, rows, key, reason)
    if not (lead.email or "").strip() and channel == "gmail":
        raise AppError("This lead has no email address")
    if channel == "gmail":
        token = getattr(actor, "gmail_refresh_token", "") or ""
        if not token:
            raise AppError("Connect Gmail or open the message in your mail app", 409)
        send_gmail(refresh_token=token, to=lead.email, subject=subject, body=body, bcc=team_bcc(db))
    message = OutreachMessage(
        lead_id=lead.id,
        user_id=actor.id,
        template_key=key,
        channel=channel,
        to_email=(lead.email or "").strip().lower(),
        subject=subject[:200],
        body=body[:8000],
        override_reason=(reason or "")[:300],
        sent_at=utcnow(),
    )
    db.add(message)
    who = lead.contact_name or lead.company
    summary = f"{actor.display_name or actor.email} reached out to {who} on {_stamp(message.sent_at)}"
    db.add(LeadEvent(lead_id=lead.id, actor_id=actor.id, summary=summary[:400]))
    if lead.status == "New":
        lead.status = "Contacted"
    span = days if days and days > 0 else 7
    follow = FollowUp(
        lead_id=lead.id,
        user_id=actor.id,
        title=f"Follow up with {lead.company}"[:300],
        notes=f"After {key.replace('_', ' ')}",
        due_at=utcnow() + timedelta(days=span),
        status="open",
    )
    db.add(follow)
    db.commit()
    db.refresh(message)
    return {"message": _public(db, message), "summary": summary, "followup_due": follow.due_at.isoformat()}


def latest_labels(db: Session, lead_ids: list[int]) -> dict[int, str]:
    if not lead_ids:
        return {}
    rows = db.scalars(
        select(OutreachMessage).where(OutreachMessage.lead_id.in_(lead_ids)).order_by(OutreachMessage.id.desc())
    ).all()
    found: dict[int, OutreachMessage] = {}
    for row in rows:
        found.setdefault(row.lead_id, row)
    labels = {}
    for lead_id, row in found.items():
        user = db.get(User, row.user_id)
        name = user.display_name if user and user.display_name else "A teammate"
        labels[lead_id] = f"Contacted by {name} on {_stamp(row.sent_at)}"
    return labels


def due_today(db: Session, actor: User) -> list[dict]:
    now = utcnow()
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    absent = list(db.scalars(select(User).where(User.on_leave.is_(True), User.cover_user_id == actor.id)).all())
    absent_ids = [user.id for user in absent]
    rows = db.scalars(
        select(FollowUp).where(FollowUp.status == "open", FollowUp.due_at.is_not(None), FollowUp.due_at <= end)
    ).all()
    items = []
    for row in rows:
        lead = db.get(Lead, row.lead_id) if row.lead_id else None
        mine = row.user_id == actor.id
        covered = lead is not None and lead.owner_id in absent_ids
        if not mine and not covered:
            continue
        items.append({
            "followup_id": row.id,
            "lead_id": row.lead_id,
            "company": lead.company if lead else "",
            "title": row.title,
            "due_at": row.due_at.isoformat() if row.due_at else None,
            "covering": covered and not mine,
        })
    return items


def take_over(db: Session, actor: User, lead: Lead) -> dict:
    previous = lead.owner_id
    lead.owner_id = actor.id
    db.add(LeadEvent(
        lead_id=lead.id,
        actor_id=actor.id,
        summary=f"{actor.display_name or actor.email} took over the lead on {_stamp(utcnow())}"[:400],
    ))
    db.commit()
    return {"lead_id": lead.id, "owner_id": actor.id, "previous_owner_id": previous}


def timeline(db: Session, lead: Lead) -> list[dict]:
    from app.models import Comment

    items = []
    for event in db.scalars(select(LeadEvent).where(LeadEvent.lead_id == lead.id)).all():
        items.append({"at": event.created_at, "summary": event.summary})
    for note in db.scalars(select(Comment).where(Comment.lead_id == lead.id)).all():
        author = db.get(User, note.author_id)
        name = author.display_name if author and author.display_name else "Someone"
        items.append({"at": note.created_at, "summary": f"{name} added a note on {_stamp(note.created_at)}"})
    items.sort(key=lambda item: item["at"] or utcnow(), reverse=True)
    return [{"summary": item["summary"], "at": item["at"].isoformat() if item["at"] else None} for item in items]
