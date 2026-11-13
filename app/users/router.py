"""User administration and team directory."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_module
from app.core.permissions import MODULES
from app.models import User
from app.users.service import decide_access, list_users, role_matrix, serialize_user, set_role, set_role_permissions, set_user_permissions

router = APIRouter(prefix="/api")


@router.get("/team")
def team(db: Session = Depends(get_db), _user=Depends(require_module("team"))):
    rows = db.scalars(select(User).where(User.status == "approved").order_by(User.display_name)).all()
    return [
        {"id": row.id, "name": row.display_name, "email": row.email, "role": row.role, "last_login_at": row.last_login_at.isoformat() if row.last_login_at else None}
        for row in rows
    ]


@router.get("/users")
def users(db: Session = Depends(get_db), _user=Depends(require_module("users"))):
    return {"modules": [{"key": key, "label": label} for key, label in MODULES], "users": list_users(db), "roles": role_matrix(db)}


@router.get("/users/{user_id}")
def user_detail(user_id: int, db: Session = Depends(get_db), _user=Depends(require_module("users"))):
    row = db.get(User, user_id)
    if row is None:
        from fastapi import HTTPException

        raise HTTPException(404, "User not found")
    return serialize_user(db, row, include_permissions=True)


@router.post("/users/{user_id}/decision")
def decision(user_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("users", manage=True))):
    target = decide_access(db, actor, user_id, str(body.get("decision") or ""))
    return serialize_user(db, target)


@router.patch("/users/{user_id}")
def patch_user(user_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("users", manage=True))):
    target = set_role(db, actor, user_id, str(body.get("role") or ""))
    return serialize_user(db, target)


@router.put("/users/{user_id}/permissions")
def put_user_permissions(user_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("users", manage=True))):
    target = set_user_permissions(db, actor, user_id, body.get("permissions") or {})
    return serialize_user(db, target, include_permissions=True)


@router.put("/permissions/roles/{role}")
def put_role_permissions(role: str, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("users", manage=True))):
    set_role_permissions(db, actor, role, body.get("permissions") or {})
    return {"role": role, "permissions": role_matrix(db).get(role, {})}
