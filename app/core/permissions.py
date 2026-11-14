"""Module catalog and default role permissions.

Super Admin always has every module. Admin and Member defaults are stored in
the database so an administrator can change them; the backend reads those rows
on every request.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

MODULES = [
    ("dashboard", "Dashboard"),
    ("leads", "Leads"),
    ("pipeline", "Sales pipeline"),
    ("followups", "Follow-ups"),
    ("team", "Team"),
    ("reports", "Reports"),
    ("social", "Social"),
    ("pulse", "Industry Pulse"),
    ("grokbot", "GrokBot Agent Workspace"),
    ("users", "User administration"),
    ("search", "Search criteria"),
    ("apikeys", "API key management"),
    ("ai", "AI / LLM configuration"),
    ("geo", "Geographic targeting"),
    ("activity", "User activity monitor"),
    ("comments", "Comments & updates"),
    ("settings", "Workspace settings"),
]

MODULE_KEYS = [key for key, _label in MODULES]
MODULE_LABELS = dict(MODULES)


def _all(view: bool, manage: bool) -> dict:
    return {key: {"view": view, "manage": manage} for key in MODULE_KEYS}


def _only(granted: dict) -> dict:
    table = _all(False, False)
    table.update(granted)
    return table


DEFAULT_ROLE_PERMISSIONS = {
    "super_admin": _all(True, True),
    "admin": _all(True, True),
    "member": _only(
        {
            "dashboard": {"view": True, "manage": False},
            "leads": {"view": True, "manage": True},
            "pipeline": {"view": True, "manage": False},
            "followups": {"view": True, "manage": True},
            "team": {"view": True, "manage": False},
            "reports": {"view": True, "manage": False},
            "social": {"view": True, "manage": True},
            "pulse": {"view": True, "manage": True},
            "grokbot": {"view": True, "manage": True},
            "search": {"view": True, "manage": True},
            "ai": {"view": True, "manage": False},
            "geo": {"view": True, "manage": True},
            "comments": {"view": True, "manage": True},
        }
    ),
}


def effective_permission(db: Session, user, module: str) -> dict:
    from app.models import RolePermission, UserPermission

    if user.role == "super_admin":
        return {"view": True, "manage": True}
    override = db.scalar(
        select(UserPermission).where(UserPermission.user_id == user.id, UserPermission.module == module)
    )
    if override is not None:
        return {"view": bool(override.can_view), "manage": bool(override.can_manage)}
    role_row = db.scalar(
        select(RolePermission).where(RolePermission.role == user.role, RolePermission.module == module)
    )
    if role_row is None:
        return {"view": False, "manage": False}
    return {"view": bool(role_row.can_view), "manage": bool(role_row.can_manage)}


def permission_map(db: Session, user) -> dict:
    return {module: effective_permission(db, user, module) for module in MODULE_KEYS}


def has_permission(db: Session, user, module: str, manage: bool = False) -> bool:
    if getattr(user, "status", None) != "approved":
        return False
    flags = effective_permission(db, user, module)
    if manage:
        return flags["manage"]
    return flags["view"] or flags["manage"]
