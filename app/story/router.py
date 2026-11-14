"""Story lines and the overlay kill switch."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.story.service import lines_map, overlay_enabled, reset_line, save_line, set_overlay

router = APIRouter()


def _admin(user) -> None:
    if user.role not in {"admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="Admin only")


@router.get("/api/story/overlay")
def get_overlay(_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return {"enabled": overlay_enabled(db)}


@router.put("/api/admin/story-overlay")
def put_overlay(body: dict, user=Depends(get_current_user), db: Session = Depends(get_db)):
    _admin(user)
    return {"enabled": set_overlay(db, bool(body.get("enabled")))}


@router.get("/api/story/lines")
def get_lines(_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return {"lines": lines_map(db)}


@router.put("/api/admin/story-messages")
def put_message(body: dict, user=Depends(get_current_user), db: Session = Depends(get_db)):
    _admin(user)
    row = save_line(db, str(body.get("scene_id") or ""), str(body.get("actor") or ""), str(body.get("text") or ""), user.email)
    return {"scene_id": row.scene_id, "actor": row.actor, "text": row.text}


@router.post("/api/admin/story-messages/reset")
def post_reset(body: dict, user=Depends(get_current_user), db: Session = Depends(get_db)):
    _admin(user)
    reset_line(db, str(body.get("scene_id") or ""), str(body.get("actor") or ""))
    return {"ok": True}
