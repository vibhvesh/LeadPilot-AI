"""Request dependencies for the current user and module permissions."""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.service import user_from_request
from app.core.database import get_db
from app.core.permissions import has_permission


def get_current_user(request: Request, db: Session = Depends(get_db)):
    cached = getattr(request.state, "user", None)
    user = cached or user_from_request(db, request)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign-in required")
    if user.status != "approved":
        raise HTTPException(status_code=403, detail="Account is not approved")
    request.state.user = user
    return user


def require_module(module: str, manage: bool = False):
    def dependency(user=Depends(get_current_user), db: Session = Depends(get_db)):
        if not has_permission(db, user, module, manage=manage):
            action = "manage" if manage else "view"
            raise HTTPException(status_code=403, detail=f"Missing permission to {action} {module}")
        return user

    return dependency
