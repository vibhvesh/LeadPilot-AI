"""Write audit events in the caller's transaction."""

from sqlalchemy.orm import Session

from app.models import AuditEvent


def record(
    db: Session,
    *,
    action: str,
    module: str = "",
    target: str = "",
    detail: dict | None = None,
    success: bool = True,
    user=None,
    email: str = "",
    ip_address: str = "",
    note: str = "",
) -> AuditEvent:
    event = AuditEvent(
        user_id=getattr(user, "id", None),
        email=email or getattr(user, "email", "") or "",
        action=action,
        module=module,
        target=str(target)[:200],
        detail=detail or {},
        success=success,
        ip_address=(ip_address or "")[:80],
        note=note[:2000],
    )
    db.add(event)
    return event
