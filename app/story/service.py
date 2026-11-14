"""Read and write story lines. Defaults live in the page script; the database stores edits."""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.story import StoryMessage
from app.models.workspace import WorkspaceSettings

_SCENE = re.compile(r"^s\d{2}$")
_ACTOR = re.compile(r"^[a-z0-9-]{1,40}$")


def lines_map(db: Session) -> dict[str, str]:
    rows = db.scalars(select(StoryMessage)).all()
    return {f"{row.scene_id}:{row.actor}": row.text for row in rows}


def save_line(db: Session, scene_id: str, actor: str, text: str, updated_by: str) -> StoryMessage:
    scene_id = (scene_id or "").strip()
    actor = (actor or "").strip()
    text = (text or "").strip()
    if not _SCENE.match(scene_id) or not _ACTOR.match(actor):
        raise AppError("Unknown scene or speaker", 400)
    if not text or len(text) > 240:
        raise AppError("Line must be 1 to 240 characters", 400)
    row = db.scalar(select(StoryMessage).where(StoryMessage.scene_id == scene_id, StoryMessage.actor == actor))
    if row is None:
        row = StoryMessage(scene_id=scene_id, actor=actor, text=text, updated_by=updated_by)
        db.add(row)
    else:
        row.text = text
        row.updated_by = updated_by
    db.commit()
    db.refresh(row)
    return row


def reset_line(db: Session, scene_id: str, actor: str) -> None:
    scene_id = (scene_id or "").strip()
    actor = (actor or "").strip()
    if not _SCENE.match(scene_id) or not _ACTOR.match(actor):
        raise AppError("Unknown scene or speaker", 400)
    row = db.scalar(select(StoryMessage).where(StoryMessage.scene_id == scene_id, StoryMessage.actor == actor))
    if row is not None:
        db.delete(row)
        db.commit()


def overlay_enabled(db: Session) -> bool:
    row = db.get(WorkspaceSettings, 1)
    if row is None or row.story_overlay_enabled is None:
        return False
    return bool(row.story_overlay_enabled)


def set_overlay(db: Session, enabled: bool) -> bool:
    row = db.get(WorkspaceSettings, 1)
    if row is None:
        raise AppError("Workspace is not ready", 404)
    row.story_overlay_enabled = bool(enabled)
    db.commit()
    return bool(row.story_overlay_enabled)
