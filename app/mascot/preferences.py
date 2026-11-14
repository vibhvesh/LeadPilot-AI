"""Validate and store mascot preferences. Unknown characters are refused."""

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import has_permission
from app.models import User, WorkspaceSettings

CHARACTERS = (
    "hanuman",
    "mango",
    "noodle",
    "pickle",
    "biscuit",
    "rama",
    "lakshmana",
    "sita",
    "jambavan",
    "jatayu",
    "sugriva",
    "vibhishana",
    "ravana",
    "krishna",
    "arjuna",
    "bhima",
    "karna",
    "draupadi",
    "bhishma",
    "shakuni",
    "ghatotkacha",
)
TONES = ("polite", "cheeky", "savage")
SIZES = ("small", "medium", "large")
SIDES = ("left", "right")
IDLE_MIN = 1500
IDLE_MAX = 10000
IDLE_DEFAULT = 2600


def workspace_character(db: Session) -> str:
    row = db.get(WorkspaceSettings, 1)
    name = (row.mascot_character if row is not None else "") or "hanuman"
    return name if name in CHARACTERS else "hanuman"


def _raw(user: User) -> dict:
    value = user.preferences
    return dict(value) if isinstance(value, dict) else {}


def resolve(db: Session, user: User) -> dict:
    raw = _raw(user)
    default = workspace_character(db)
    character = raw.get("character") or default
    if character not in CHARACTERS:
        character = "hanuman"
    idle = raw.get("idle_ms", IDLE_DEFAULT)
    try:
        idle = int(idle)
    except (TypeError, ValueError):
        idle = IDLE_DEFAULT
    if idle < IDLE_MIN or idle > IDLE_MAX:
        idle = IDLE_DEFAULT
    return {
        "character": character,
        "enabled": raw["enabled"] if isinstance(raw.get("enabled"), bool) else True,
        "idle_ms": idle,
        "tone": raw.get("tone") if raw.get("tone") in TONES else "cheeky",
        "size": raw.get("size") if raw.get("size") in SIZES else "medium",
        "side": raw.get("side") if raw.get("side") in SIDES else "right",
        "workspace_default": default,
        "explicit": bool(raw),
        "can_set_default": has_permission(db, user, "settings", manage=True),
    }


def save(db: Session, user: User, body: dict) -> dict:
    if not isinstance(body, dict):
        raise AppError("Send mascot preferences as JSON")
    current = _raw(user)
    if body.get("character"):
        name = str(body["character"]).strip()
        if name not in CHARACTERS:
            raise AppError("Choose a character from the cast")
        current["character"] = name
    if "enabled" in body:
        current["enabled"] = bool(body.get("enabled"))
    if body.get("idle_ms") is not None and "idle_ms" in body:
        try:
            idle = int(body.get("idle_ms"))
        except (TypeError, ValueError) as exc:
            raise AppError("Idle time must be between 1.5 and 10 seconds") from exc
        if idle < IDLE_MIN or idle > IDLE_MAX:
            raise AppError("Idle time must be between 1.5 and 10 seconds")
        current["idle_ms"] = idle
    if body.get("tone"):
        tone = str(body["tone"])
        if tone not in TONES:
            raise AppError("Tone must be polite, cheeky, or savage")
        current["tone"] = tone
    if body.get("size"):
        size = str(body["size"])
        if size not in SIZES:
            raise AppError("Size must be small, medium, or large")
        current["size"] = size
    if body.get("side"):
        side = str(body["side"])
        if side not in SIDES:
            raise AppError("Side must be left or right")
        current["side"] = side
    user.preferences = current
    db.commit()
    db.refresh(user)
    return resolve(db, user)


def set_workspace_default(db: Session, name: str) -> str:
    character = (name or "").strip()
    if character not in CHARACTERS:
        raise AppError("Choose a character from the cast")
    row = db.get(WorkspaceSettings, 1)
    if row is None:
        row = WorkspaceSettings(id=1)
        db.add(row)
        db.flush()
    row.mascot_character = character
    db.commit()
    return character
