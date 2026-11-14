"""Approval, roles, and per-module permission edits."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record
from app.auth.service import revoke_user_sessions
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.permissions import MODULE_KEYS, permission_map
from app.models import RolePermission, User, UserPermission
from app.models.identity import utcnow

ASSIGNABLE_ROLES = {"admin", "member"}


def _guard_actor(actor: User) -> None:
    if actor.status != "approved":
        raise AppError("Account is not approved", 403)


def _protect_super_admin(target: User) -> None:
    settings = get_settings()
    if target.role == "super_admin" or target.email == settings.super_admin:
        raise AppError("The Super Admin account cannot be changed here", 403)


def list_users(db: Session) -> list[dict]:
    users = db.scalars(select(User).order_by(User.created_at.asc())).all()
    return [serialize_user(db, user) for user in users]


def serialize_user(db: Session, user: User, include_permissions: bool = False) -> dict:
    payload = {
        "id": user.id,
        "email": user.email,
        "name": user.display_name,
        "role": user.role,
        "status": user.status,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "approved_by": user.approved_by,
    }
    if include_permissions:
        payload["permissions"] = permission_map(db, user)
    return payload


def decide_access(db: Session, actor: User, user_id: int, decision: str) -> User:
    _guard_actor(actor)
    if decision not in {"approve", "reject"}:
        raise AppError("Decision must be approve or reject")
    target = db.get(User, user_id)
    if target is None:
        raise AppError("User not found", 404)
    _protect_super_admin(target)
    if decision == "approve":
        target.status = "approved"
        target.approved_at = utcnow()
        target.approved_by = actor.email
        if target.role not in ASSIGNABLE_ROLES:
            target.role = "member"
    else:
        target.status = "rejected"
        target.approved_at = utcnow()
        target.approved_by = actor.email
        revoke_user_sessions(db, target.id)
    record(
        db,
        user=actor,
        action="approval" if decision == "approve" else "rejection",
        module="users",
        target=target.email,
        detail={"decision": decision, "user_id": target.id},
    )
    db.commit()
    db.refresh(target)
    return target


def set_role(db: Session, actor: User, user_id: int, role: str) -> User:
    _guard_actor(actor)
    if role not in ASSIGNABLE_ROLES:
        raise AppError("Role must be admin or member")
    if role == "admin" and actor.role != "super_admin":
        raise AppError("Only the Super Admin can grant the Admin role", 403)
    target = db.get(User, user_id)
    if target is None:
        raise AppError("User not found", 404)
    _protect_super_admin(target)
    previous = target.role
    target.role = role
    record(
        db,
        user=actor,
        action="role_change",
        module="users",
        target=target.email,
        detail={"from": previous, "to": role},
    )
    db.commit()
    db.refresh(target)
    return target


def set_role_permissions(db: Session, actor: User, role: str, permissions: dict) -> None:
    if actor.role != "super_admin":
        raise AppError("Only the Super Admin can edit role templates", 403)
    if role == "super_admin":
        raise AppError("Super Admin permissions are fixed", 403)
    if role not in ASSIGNABLE_ROLES:
        raise AppError("Unknown role")
    _replace_role_rows(db, role, permissions)
    record(
        db,
        user=actor,
        action="permission_change",
        module="users",
        target=role,
        detail={"scope": "role", "permissions": _clean_permissions(permissions)},
    )
    db.commit()


def set_user_permissions(db: Session, actor: User, user_id: int, permissions: dict) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise AppError("User not found", 404)
    _protect_super_admin(target)
    if actor.role != "super_admin" and target.role == "admin":
        raise AppError("Only the Super Admin can edit an Admin's permissions", 403)
    existing = db.scalars(select(UserPermission).where(UserPermission.user_id == target.id)).all()
    for row in existing:
        db.delete(row)
    db.flush()
    for module, flags in _clean_permissions(permissions).items():
        db.add(
            UserPermission(
                user_id=target.id,
                module=module,
                can_view=flags["view"],
                can_manage=flags["manage"],
            )
        )
    record(
        db,
        user=actor,
        action="permission_change",
        module="users",
        target=target.email,
        detail={"scope": "user", "permissions": _clean_permissions(permissions)},
    )
    db.commit()
    db.refresh(target)
    return target


def clear_user_permissions(db: Session, actor: User, user_id: int) -> User:
    return set_user_permissions(db, actor, user_id, {})


def role_matrix(db: Session) -> dict:
    rows = db.scalars(select(RolePermission)).all()
    matrix = {role: {} for role in ("super_admin", "admin", "member")}
    for row in rows:
        matrix.setdefault(row.role, {})[row.module] = {"view": row.can_view, "manage": row.can_manage}
    return matrix


def _clean_permissions(permissions: dict) -> dict:
    cleaned = {}
    for module, flags in (permissions or {}).items():
        if module not in MODULE_KEYS or not isinstance(flags, dict):
            continue
        view = bool(flags.get("view"))
        manage = bool(flags.get("manage"))
        if manage:
            view = True
        cleaned[module] = {"view": view, "manage": manage}
    return cleaned


def _replace_role_rows(db: Session, role: str, permissions: dict) -> None:
    cleaned = _clean_permissions(permissions)
    for module in MODULE_KEYS:
        flags = cleaned.get(module, {"view": False, "manage": False})
        row = db.scalar(select(RolePermission).where(RolePermission.role == role, RolePermission.module == module))
        if row is None:
            db.add(RolePermission(role=role, module=module, can_view=flags["view"], can_manage=flags["manage"]))
        else:
            row.can_view = flags["view"]
            row.can_manage = flags["manage"]
