"""Three shared templates. Admins edit the text; merge fields fill in the person."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.outreach import TEMPLATE_KEYS, OutreachTemplate

SEED = {
    "first": (
        "First Outreach",
        "Introduction from {{sender_name}}",
        "Hello {{first_name}},\n\nI am {{sender_name}}. I am writing because {{company}} may be hiring for roles we can help staff.\n\nIf a short call is useful, reply to this note and I will send times.\n\n{{sender_name}}",
    ),
    "followup_1": (
        "Follow-up 1",
        "Following up, {{first_name}}",
        "Hello {{first_name}},\n\nI sent a note last week about supporting hiring at {{company}}. I am still happy to share how we staff US roles.\n\n{{sender_name}}",
    ),
    "followup_2": (
        "Follow-up 2",
        "One more note for {{company}}",
        "Hello {{first_name}},\n\nThis is my last planned note. If hiring at {{company}} is quiet for now, no reply is needed. If it would help to talk, I am here.\n\n{{sender_name}}",
    ),
}


def ensure_templates(db: Session) -> list[OutreachTemplate]:
    rows = list(db.scalars(select(OutreachTemplate)).all())
    have = {row.key for row in rows}
    for key in TEMPLATE_KEYS:
        if key in have:
            continue
        name, subject, body = SEED[key]
        row = OutreachTemplate(key=key, name=name, subject=subject, body=body)
        db.add(row)
        rows.append(row)
    if len(have) < len(TEMPLATE_KEYS):
        db.commit()
    return rows


def render(text: str, fields: dict) -> str:
    out = text or ""
    for key, value in fields.items():
        out = out.replace("{{" + key + "}}", value or "")
    return out


def fields_for(lead, actor) -> dict:
    full = (lead.contact_name or "").strip()
    first = full.split()[0] if full else "there"
    return {
        "first_name": first,
        "full_name": full or "there",
        "company": lead.company or "",
        "sender_name": (actor.display_name or actor.email or "").strip(),
        "sender_email": actor.email or "",
    }


def save_template(db: Session, key: str, subject: str, body: str) -> OutreachTemplate:
    if key not in TEMPLATE_KEYS:
        raise AppError("Unknown template")
    ensure_templates(db)
    row = db.scalar(select(OutreachTemplate).where(OutreachTemplate.key == key))
    row.subject = (subject or "")[:200]
    row.body = (body or "")[:8000]
    db.commit()
    db.refresh(row)
    return row
