"""One lightweight, role-aware snapshot for the cockpit homepage.

Counts come from the database. A section the caller cannot view is null
so the page does not invent a zero for data they are not allowed to see.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, not_, nulls_last, select
from sqlalchemy.orm import Session

from app.core.permissions import has_permission
from app.models import (
    LEAD_STATUSES,
    AuditEvent,
    DeepSearchRequest,
    FollowUp,
    Lead,
    PulseItem,
    SocialItem,
    User,
)
from app.providers.llm import provider_catalog, select_provider
from app.search.providers import active_search_backends

REFRESH_SECONDS = 60


def summary(db: Session, actor: User) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "generated_at": now.isoformat(),
        "refresh_seconds": REFRESH_SECONDS,
        "role": actor.role,
        "leads": _leads(db, now),
        "followups": _followups(db, actor, now),
        "social": _social(db, actor),
        "pulse": _pulse(db, actor),
        "bot": _bot(db, actor),
        "health": _health(db, actor),
        "team": _team(db, actor),
        "activity": _activity(db, actor),
        "approvals": _approvals(db, actor),
    }


def _allow(db: Session, actor: User, module: str) -> bool:
    return has_permission(db, actor, module)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _count(db: Session, model, *clauses) -> int:
    statement = select(func.count()).select_from(model)
    if clauses:
        statement = statement.where(*clauses)
    return db.scalar(statement) or 0


def _leads(db: Session, now: datetime) -> dict:
    total = _count(db, Lead)
    counts = {status: 0 for status in LEAD_STATUSES}
    for status, count in db.execute(select(Lead.status, func.count()).group_by(Lead.status)).all():
        key = status if status in counts else "New"
        counts[key] = counts.get(key, 0) + count
    won = counts.get("Won", 0)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week = now - timedelta(days=7)
    prior = now - timedelta(days=14)
    pipeline_value = db.scalar(
        select(func.coalesce(func.sum(Lead.estimated_value), 0)).where(Lead.status.in_(("New", "Contacted", "Qualified")))
    )
    return {
        "total": total,
        "new_today": _count(db, Lead, Lead.created_at >= today),
        "new_this_week": _count(db, Lead, Lead.created_at >= week),
        "by_status": counts,
        "top_uncontacted": _top_uncontacted(db),
        "conversion_rate": (won / total) if total else 0,
        "pipeline_value": int(pipeline_value or 0),
        "contact": _contact(db, total),
        "trend": _trend(db, now, prior),
    }


def _top_uncontacted(db: Session) -> list[dict]:
    rows = db.scalars(
        select(Lead).where(Lead.status == "New").order_by(nulls_last(Lead.score.desc()), Lead.id.desc()).limit(5)
    ).all()
    return [{"id": row.id, "company": row.company, "score": row.score, "status": row.status} for row in rows]


def _filled(column):
    return func.length(func.trim(func.coalesce(column, ""))) > 0


def _contact(db: Session, total: int) -> dict:
    email_ok = _filled(Lead.email)
    phone_ok = _filled(Lead.phone)
    full = _count(db, Lead, and_(email_ok, phone_ok))
    phone_only = _count(db, Lead, and_(phone_ok, not_(email_ok)))
    email_only = _count(db, Lead, and_(email_ok, not_(phone_ok)))
    return {
        "full": full,
        "phone_only": phone_only,
        "email_only": email_only,
        "missing": max(0, total - full - phone_only - email_only),
    }


def _trend(db: Session, now: datetime, since: datetime) -> dict:
    counts: dict[str, int] = {}
    for stamp in db.scalars(select(Lead.created_at).where(Lead.created_at >= since)).all():
        if stamp is None:
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        key = stamp.astimezone(timezone.utc).date().isoformat()
        counts[key] = counts.get(key, 0) + 1
    today = now.astimezone(timezone.utc).date()
    days = []
    this_week = 0
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        count = counts.get(day.isoformat(), 0)
        days.append({"date": day.isoformat(), "count": count})
        this_week += count
    previous = 0
    for offset in range(13, 6, -1):
        previous += counts.get((today - timedelta(days=offset)).isoformat(), 0)
    delta = this_week - previous
    scale = max(this_week, previous, 1)
    pitch = delta / scale
    if pitch > 1:
        pitch = 1.0
    elif pitch < -1:
        pitch = -1.0
    return {
        "days": days,
        "this_week": this_week,
        "previous_week": previous,
        "delta": delta,
        "pitch": round(pitch, 4),
    }


def _followups(db: Session, actor: User, now: datetime):
    if not _allow(db, actor, "followups"):
        return None
    open_count = _count(db, FollowUp, FollowUp.status == "open")
    overdue = _count(
        db,
        FollowUp,
        FollowUp.status == "open",
        FollowUp.due_at.is_not(None),
        FollowUp.due_at < now,
    )
    return {"open": open_count, "overdue": overdue}


def _social(db: Session, actor: User):
    if not _allow(db, actor, "social"):
        return None
    newest = _social_rows(db, "reply")
    discussions = _social_rows(db, "engage")
    return {
        "reply": _count(db, SocialItem, SocialItem.status == "open", SocialItem.bucket == "reply"),
        "engage": _count(db, SocialItem, SocialItem.status == "open", SocialItem.bucket == "engage"),
        "newest_replies": [_social_brief(row) for row in newest],
        "newest_discussions": [_social_brief(row) for row in discussions],
    }


def _social_rows(db: Session, bucket: str):
    return db.scalars(
        select(SocialItem)
        .where(SocialItem.status == "open", SocialItem.bucket == bucket)
        .order_by(SocialItem.created_at.desc(), SocialItem.id.desc())
        .limit(3)
    ).all()


def _social_brief(row: SocialItem) -> dict:
    return {
        "id": row.id,
        "snippet": (row.snippet or row.topic or "Open item")[:140],
        "platform": row.platform or "",
        "poster_name": row.poster_name or "",
    }


def _pulse(db: Session, actor: User):
    if not _allow(db, actor, "pulse"):
        return None
    rows = db.scalars(
        select(PulseItem)
        .where(PulseItem.status == "open", PulseItem.urgency == "urgent")
        .order_by(PulseItem.created_at.desc(), PulseItem.id.desc())
        .limit(3)
    ).all()
    return {
        "urgent": _count(db, PulseItem, PulseItem.status == "open", PulseItem.urgency == "urgent"),
        "urgent_items": [{"id": row.id, "headline": (row.headline or "Urgent story")[:140]} for row in rows],
    }


def _bot(db: Session, actor: User):
    if not (_allow(db, actor, "search") or _allow(db, actor, "grokbot")):
        return None
    requests = {"pending": 0, "claimed": 0, "completed": 0, "other": 0}
    for status, count in db.execute(select(DeepSearchRequest.status, func.count()).group_by(DeepSearchRequest.status)).all():
        if status in ("pending", "claimed", "completed"):
            requests[status] = count
        else:
            requests["other"] += count
    webhook_failed = _count(db, DeepSearchRequest, DeepSearchRequest.webhook_status == "failed")
    lead_at = db.scalar(select(func.max(Lead.created_at)).where(Lead.source == "grokbot"))
    social_at = db.scalar(select(func.max(SocialItem.created_at)).where(SocialItem.source == "bot"))
    pulse_at = db.scalar(select(func.max(PulseItem.created_at)).where(PulseItem.origin == "bot"))
    stamps = [stamp for stamp in (lead_at, social_at, pulse_at) if stamp is not None]
    latest = max(stamps) if stamps else None
    return {
        "last_ingest_at": _iso(latest),
        "sources": {"leads": _iso(lead_at), "social": _iso(social_at), "pulse": _iso(pulse_at)},
        "requests": requests,
        "webhook_failed": webhook_failed,
    }


def _database_ok(db: Session) -> bool:
    try:
        db.execute(select(1))
    except Exception:
        return False
    return True


def _health(db: Session, actor: User) -> dict:
    provider, _model, _note = select_provider(db)
    backends = active_search_backends(db)
    keys = None
    if _allow(db, actor, "apikeys"):
        keys = [{"provider": row["provider"], "configured": bool(row["configured"])} for row in provider_catalog(db)]
    return {
        "api": "ok",
        "database": "ok" if _database_ok(db) else "error",
        "llm_present": bool(provider),
        "llm_provider": provider or "",
        "search_present": bool(backends),
        "search_provider": backends[0] if backends else "",
        "keys": keys,
    }


def _team(db: Session, actor: User):
    if not _allow(db, actor, "team"):
        return None
    approved = _count(db, User, User.status == "approved")
    rows = db.scalars(
        select(User)
        .where(User.status == "approved")
        .order_by(nulls_last(User.last_login_at.desc()), User.display_name)
        .limit(8)
    ).all()
    return {
        "approved": approved,
        "roster": [
            {
                "name": row.display_name or "",
                "email": row.email,
                "role": row.role,
                "last_login_at": _iso(row.last_login_at),
            }
            for row in rows
        ],
    }


def _activity(db: Session, actor: User):
    if not _allow(db, actor, "activity"):
        return None
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today = _count(db, AuditEvent, AuditEvent.created_at >= start)
    failed = _count(db, AuditEvent, AuditEvent.created_at >= start, AuditEvent.success.is_(False))
    rows = db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(6)).all()
    return {
        "activities_today": today,
        "failed_today": failed,
        "recent": [
            {
                "email": row.email,
                "action": row.action,
                "module": row.module,
                "success": bool(row.success),
                "created_at": _iso(row.created_at),
            }
            for row in rows
        ],
    }


def _approvals(db: Session, actor: User):
    if not _allow(db, actor, "users"):
        return None
    return {
        "pending": _count(db, User, User.status == "pending"),
        "approved": _count(db, User, User.status == "approved"),
    }
