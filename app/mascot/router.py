"""Mascot preferences for the signed-in person, plus the workspace default."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.database import get_db
from app.core.deps import get_current_user, require_module
from app.mascot.preferences import resolve, save, set_workspace_default

router = APIRouter()


@router.get("/api/me/preferences")
def get_preferences(db: Session = Depends(get_db), actor=Depends(get_current_user)):
    return resolve(db, actor)


@router.put("/api/me/preferences")
def put_preferences(body: dict, db: Session = Depends(get_db), actor=Depends(get_current_user)):
    saved = save(db, actor, body or {})
    record(db, user=actor, action="mascot_preferences", module="dashboard", target=str(actor.id), detail={
        "character": saved["character"],
        "enabled": saved["enabled"],
        "tone": saved["tone"],
        "size": saved["size"],
        "side": saved["side"],
        "idle_ms": saved["idle_ms"],
    })
    db.commit()
    return saved


@router.put("/api/settings/mascot")
def put_default(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("settings", manage=True))):
    character = set_workspace_default(db, str((body or {}).get("character") or ""))
    record(db, user=actor, action="mascot_default", module="settings", target=character, detail={"character": character})
    db.commit()
    return {"character": character}
