"""Counts for the dashboard, pipeline, and reports. All figures come from the database."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import has_permission
from app.leads.service import lead_dict
from app.models import LEAD_STATUSES, AuditEvent, FollowUp, Lead, SearchCriteria, SearchRun, User


def _start_of_month() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _start_of_day() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def status_counts(db: Session) -> dict:
    rows = db.execute(select(Lead.status, func.count()).group_by(Lead.status)).all()
    counts = {status: 0 for status in LEAD_STATUSES}
    for status, count in rows:
        counts[status or "New"] = counts.get(status, 0) + count
    return counts


def dashboard(db: Session, actor: User) -> dict:
    total = db.scalar(select(func.count()).select_from(Lead)) or 0
    counts = status_counts(db)
    qualified = counts.get("Qualified", 0)
    won = counts.get("Won", 0)
    pipeline_value = db.scalar(
        select(func.coalesce(func.sum(Lead.estimated_value), 0)).where(Lead.status.in_(("New", "Contacted", "Qualified")))
    )
    due = db.scalar(select(func.count()).select_from(FollowUp).where(FollowUp.status == "open")) or 0
    recent_rows = db.scalars(select(Lead).order_by(Lead.id.desc()).limit(6)).all()
    payload = {
        "total_leads": total,
        "qualified_leads": qualified,
        "new_this_week": _new_since(db, days=7),
        "followups_due": due,
        "pipeline_value": int(pipeline_value or 0),
        "conversion_rate": (won / total) if total else 0,
        "by_status": counts,
        "recent_leads": [lead_dict(lead) for lead in recent_rows],
        "admin": None,
    }
    if has_permission(db, actor, "users"):
        pending = db.scalar(select(func.count()).select_from(User).where(User.status == "pending")) or 0
        approved = db.scalar(select(func.count()).select_from(User).where(User.status == "approved")) or 0
        payload["admin"] = {"pending": pending, "approved": approved, "policy": "Approval required"}
    return payload


def pipeline(db: Session) -> dict:
    counts = status_counts(db)
    grouped = {}
    for status in LEAD_STATUSES:
        rows = db.scalars(select(Lead).where(Lead.status == status).order_by(Lead.updated_at.desc()).limit(8)).all()
        grouped[status] = [lead_dict(row) for row in rows]
    return {"counts": counts, "columns": grouped}


def reports(db: Session) -> dict:
    total = db.scalar(select(func.count()).select_from(Lead)) or 0
    counts = status_counts(db)
    month = _start_of_month()
    leads_this_month = db.scalar(select(func.count()).select_from(Lead).where(Lead.created_at >= month)) or 0
    qualified = counts.get("Qualified", 0) + counts.get("Won", 0)
    won = counts.get("Won", 0)
    campaigns = db.scalar(select(func.count()).select_from(SearchCriteria)) or 0
    runs = db.scalar(select(func.count()).select_from(SearchRun).where(SearchRun.created_at >= month)) or 0
    regions = db.execute(
        select(Lead.country, func.count()).where(Lead.country != "").group_by(Lead.country).order_by(func.count().desc()).limit(6)
    ).all()
    return {
        "leads_this_month": leads_this_month,
        "qualified": qualified,
        "won": won,
        "conversion_rate": (won / total) if total else 0,
        "qualification_rate": (qualified / total) if total else 0,
        "active_campaigns": campaigns,
        "searches_this_month": runs,
        "by_status": counts,
        "by_country": [{"country": country, "count": count} for country, count in regions],
    }


def activity_summary(db: Session) -> dict:
    start = _start_of_day()
    today = db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.created_at >= start)) or 0
    api_calls = db.scalar(
        select(func.count()).select_from(AuditEvent).where(AuditEvent.created_at >= start, AuditEvent.action == "api_call")
    ) or 0
    searches = db.scalar(
        select(func.count()).select_from(AuditEvent).where(AuditEvent.created_at >= start, AuditEvent.action == "search")
    ) or 0
    failed = db.scalar(
        select(func.count()).select_from(AuditEvent).where(AuditEvent.created_at >= start, AuditEvent.success.is_(False))
    ) or 0
    return {"activities_today": today, "api_calls": api_calls, "searches": searches, "failed_requests": failed}


def _new_since(db: Session, days: int) -> int:
    from datetime import timedelta

    since = datetime.now(timezone.utc) - timedelta(days=days)
    return db.scalar(select(func.count()).select_from(Lead).where(Lead.created_at >= since)) or 0
