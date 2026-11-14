"""Outreach templates, send, coverage, and the due-today list."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_module
from app.core.errors import AppError
from app.models import Lead, User
from app.models.outreach import LeadEvent
from app.outreach.service import due_today, preview, record_send, set_team_bcc, take_over, team_bcc, timeline
from app.outreach.templates import ensure_templates, save_template

router = APIRouter()


def _lead(db: Session, lead_id: int) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise AppError("Lead not found", 404)
    return lead


@router.get("/api/outreach/templates")
def get_templates(db: Session = Depends(get_db), _user=Depends(require_module("leads"))):
    rows = ensure_templates(db)
    return {"templates": [{"key": row.key, "name": row.name, "subject": row.subject, "body": row.body} for row in rows], "team_bcc": team_bcc(db)}


@router.put("/api/outreach/templates/{key}")
def put_template(key: str, body: dict, db: Session = Depends(get_db), _user=Depends(require_module("settings", manage=True))):
    row = save_template(db, key, str(body.get("subject") or ""), str(body.get("body") or ""))
    return {"key": row.key, "name": row.name, "subject": row.subject, "body": row.body}


@router.put("/api/outreach/bcc")
def put_bcc(body: dict, db: Session = Depends(get_db), _user=Depends(require_module("settings", manage=True))):
    return {"team_bcc": set_team_bcc(db, str(body.get("team_bcc") or ""))}


@router.get("/api/leads/{lead_id}/outreach")
def get_preview(lead_id: int, template_key: str = "first", db: Session = Depends(get_db), actor=Depends(require_module("leads"))):
    return preview(db, actor, _lead(db, lead_id), template_key)


@router.post("/api/leads/{lead_id}/outreach")
def post_outreach(lead_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("leads", manage=True))):
    lead = _lead(db, lead_id)
    key = str(body.get("template_key") or "first")
    channel = str(body.get("channel") or "mailto")
    data = fields_for(lead, actor)
    subject = str(body.get("subject") or render("", data))
    text = str(body.get("body") or "")
    days = int(body.get("followup_days") or 7)
    reason = str(body.get("override_reason") or "")
    if channel == "mailto":
        raise AppError("Open the draft in your mail app, then confirm that you sent it", 409)
    try:
        return record_send(db, actor, lead, key=key, channel=channel, subject=subject, body=text, days=days, reason=reason)
    except AppError:
        raise
    except Exception as exc:
        raise AppError("Gmail did not accept the message. Use your mail app instead.", 502) from exc


@router.post("/api/leads/{lead_id}/outreach/confirm")
def confirm_outreach(lead_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("leads", manage=True))):
    lead = _lead(db, lead_id)
    return record_send(
        db,
        actor,
        lead,
        key=str(body.get("template_key") or "first"),
        channel="mailto",
        subject=str(body.get("subject") or ""),
        body=str(body.get("body") or ""),
        days=int(body.get("followup_days") or 7),
        reason=str(body.get("override_reason") or ""),
    )


@router.get("/api/leads/{lead_id}/activity")
def get_activity(lead_id: int, db: Session = Depends(get_db), _user=Depends(require_module("leads"))):
    return {"events": timeline(db, _lead(db, lead_id))}


@router.post("/api/leads/{lead_id}/note")
def post_note(lead_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("leads", manage=True))):
    from app.models import Comment

    lead = _lead(db, lead_id)
    text = str(body.get("body") or "").strip()
    if not text:
        raise AppError("Write a note before saving")
    db.add(Comment(author_id=actor.id, lead_id=lead.id, body=text[:4000]))
    db.commit()
    return {"events": timeline(db, lead)}


@router.post("/api/leads/{lead_id}/assign")
def post_assign(lead_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("leads", manage=True))):
    lead = _lead(db, lead_id)
    user_id = int(body.get("user_id") or actor.id)
    person = db.get(User, user_id)
    if person is None:
        raise AppError("That person is not on the team", 404)
    lead.owner_id = person.id
    db.add(LeadEvent(
        lead_id=lead.id,
        actor_id=actor.id,
        summary=f"{actor.display_name or actor.email} assigned {person.display_name or person.email} as point of contact",
    ))
    db.commit()
    return {"owner_id": person.id, "owner_name": person.display_name}


@router.get("/api/outreach/due")
def get_due(db: Session = Depends(get_db), actor=Depends(require_module("followups"))):
    return {"items": due_today(db, actor)}


@router.post("/api/leads/{lead_id}/takeover")
def post_takeover(lead_id: int, db: Session = Depends(get_db), actor=Depends(require_module("leads", manage=True))):
    return take_over(db, actor, _lead(db, lead_id))


@router.put("/api/me/coverage")
def put_coverage(body: dict, db: Session = Depends(get_db), actor=Depends(get_current_user)):
    actor.on_leave = bool(body.get("on_leave"))
    cover = body.get("cover_user_id")
    actor.cover_user_id = int(cover) if cover else None
    if actor.cover_user_id and db.get(User, actor.cover_user_id) is None:
        raise AppError("Choose a teammate who can cover you", 404)
    db.commit()
    return {"on_leave": actor.on_leave, "cover_user_id": actor.cover_user_id}


@router.get("/api/outreach/gmail")
def gmail_status(actor=Depends(get_current_user)):
    settings = get_settings()
    return {"connected": bool(getattr(actor, "gmail_refresh_token", "")), "google_enabled": settings.google_enabled}


@router.get("/auth/google/gmail")
def gmail_connect():
    if not get_settings().google_enabled:
        raise HTTPException(status_code=503, detail="Google is not configured. Use the mail app instead.")
    raise HTTPException(status_code=501, detail="Gmail connect is ready when the Google client is configured.")
