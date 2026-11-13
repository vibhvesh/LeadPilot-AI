"""Per-role and per-user provider access, with daily and monthly quotas."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ProviderDenied, QuotaExceeded
from app.models import ProviderAccess, ProviderUsage
from app.models.identity import utcnow

LLM_PROVIDERS = ("xai", "gemini", "openai", "mock")
KEY_PROVIDERS = ("xai", "gemini", "openai", "tavily", "brave")


def access_rule(db: Session, user, provider: str) -> ProviderAccess | None:
    personal = db.scalar(
        select(ProviderAccess).where(ProviderAccess.provider == provider, ProviderAccess.user_id == user.id)
    )
    if personal is not None:
        return personal
    return db.scalar(
        select(ProviderAccess).where(
            ProviderAccess.provider == provider,
            ProviderAccess.role == user.role,
            ProviderAccess.user_id.is_(None),
        )
    )


def consume(db: Session, user, provider: str, amount: int = 1) -> None:
    rule = access_rule(db, user, provider)
    if rule is None or not rule.enabled:
        raise ProviderDenied(f"Access to {provider} is not enabled for this account")
    if rule.daily_quota <= 0 or rule.monthly_quota <= 0:
        raise ProviderDenied(f"Access to {provider} is disabled for this account")
    now = utcnow()
    day = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")
    day_row = _usage(db, user.id, provider, day, "day")
    month_row = _usage(db, user.id, provider, month, "month")
    if day_row.count + amount > rule.daily_quota:
        raise QuotaExceeded(f"Daily {provider} quota of {rule.daily_quota} is used up")
    if month_row.count + amount > rule.monthly_quota:
        raise QuotaExceeded(f"Monthly {provider} quota of {rule.monthly_quota} is used up")
    day_row.count += amount
    month_row.count += amount


def usage_snapshot(db: Session, user, provider: str) -> dict:
    now = utcnow()
    day = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")
    day_row = db.scalar(
        select(ProviderUsage).where(
            ProviderUsage.user_id == user.id,
            ProviderUsage.provider == provider,
            ProviderUsage.period == day,
            ProviderUsage.period_kind == "day",
        )
    )
    month_row = db.scalar(
        select(ProviderUsage).where(
            ProviderUsage.user_id == user.id,
            ProviderUsage.provider == provider,
            ProviderUsage.period == month,
            ProviderUsage.period_kind == "month",
        )
    )
    rule = access_rule(db, user, provider)
    return {
        "provider": provider,
        "enabled": bool(rule and rule.enabled),
        "daily_quota": rule.daily_quota if rule else 0,
        "monthly_quota": rule.monthly_quota if rule else 0,
        "used_today": day_row.count if day_row else 0,
        "used_this_month": month_row.count if month_row else 0,
        "scope": "user" if rule and rule.user_id else "role",
    }


def list_access(db: Session) -> list[dict]:
    rows = db.scalars(select(ProviderAccess).order_by(ProviderAccess.provider, ProviderAccess.id)).all()
    return [
        {
            "id": row.id,
            "provider": row.provider,
            "role": row.role,
            "user_id": row.user_id,
            "enabled": row.enabled,
            "daily_quota": row.daily_quota,
            "monthly_quota": row.monthly_quota,
        }
        for row in rows
    ]


def upsert_access(db: Session, payload: dict) -> dict:
    provider = (payload.get("provider") or "").strip().lower()
    if provider not in {"xai", "gemini", "openai", "search", "mock", "tavily", "brave", "ai_search"}:
        from app.core.errors import AppError

        raise AppError("Unknown provider")
    user_id = payload.get("user_id")
    role = None if user_id else (payload.get("role") or "").strip()
    if not user_id and role not in {"super_admin", "admin", "member"}:
        from app.core.errors import AppError

        raise AppError("Choose a role or a user")
    statement = select(ProviderAccess).where(ProviderAccess.provider == provider)
    if user_id:
        statement = statement.where(ProviderAccess.user_id == int(user_id))
    else:
        statement = statement.where(ProviderAccess.role == role, ProviderAccess.user_id.is_(None))
    row = db.scalar(statement)
    if row is None:
        row = ProviderAccess(provider=provider, role=role, user_id=int(user_id) if user_id else None)
        db.add(row)
    row.enabled = bool(payload.get("enabled", True))
    row.daily_quota = max(0, int(payload.get("daily_quota") or 0))
    row.monthly_quota = max(0, int(payload.get("monthly_quota") or 0))
    if row.daily_quota == 0 or row.monthly_quota == 0:
        row.enabled = False
    db.flush()
    return {
        "id": row.id,
        "provider": row.provider,
        "role": row.role,
        "user_id": row.user_id,
        "enabled": row.enabled,
        "daily_quota": row.daily_quota,
        "monthly_quota": row.monthly_quota,
    }


def _usage(db: Session, user_id: int, provider: str, period: str, kind: str) -> ProviderUsage:
    row = db.scalar(
        select(ProviderUsage).where(
            ProviderUsage.user_id == user_id,
            ProviderUsage.provider == provider,
            ProviderUsage.period == period,
            ProviderUsage.period_kind == kind,
        )
    )
    if row is None:
        row = ProviderUsage(user_id=user_id, provider=provider, period=period, period_kind=kind, count=0)
        db.add(row)
        db.flush()
    return row
