from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth.router import current_user
from app.core.database import get_db
from app.models import User, Role, AuditLog

router = APIRouter(prefix="/admin", tags=["administration"])

def require_super_admin(user: User):
    if not user.is_super_admin:
        raise HTTPException(status_code=403, detail="Super Admin access required")

@router.get("/users/pending")
def pending_users(user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_super_admin(user)
    rows = db.scalars(select(User).where(User.status == "pending").order_by(User.created_at.asc())).all()
    return [{"id": str(x.id), "email": x.email, "name": x.full_name, "created_at": x.created_at} for x in rows]

@router.post("/users/{user_id}/approve")
def approve_user(user_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_super_admin(user)
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.is_super_admin:
        raise HTTPException(status_code=400, detail="Super Admin account cannot be modified here")
    target.status = "active"
    member_role = db.scalar(select(Role).where(Role.name == "Member"))
    if member_role and member_role not in target.roles:
        target.roles.append(member_role)
    db.add(AuditLog(actor_user_id=user.id, action="users.approve", target_type="user", target_id=str(target.id)))
    db.commit()
    return {"status": "active", "user_id": str(target.id)}

@router.post("/users/{user_id}/reject")
def reject_user(user_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_super_admin(user)
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.is_super_admin:
        raise HTTPException(status_code=400, detail="Super Admin account cannot be modified here")
    target.status = "rejected"
    db.add(AuditLog(actor_user_id=user.id, action="users.reject", target_type="user", target_id=str(target.id)))
    db.commit()
    return {"status": "rejected", "user_id": str(target.id)}
