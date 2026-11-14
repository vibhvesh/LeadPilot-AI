"""Signed-in Industry Pulse API."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.database import get_db
from app.core.deps import require_module
from app.pulse.fetch import pull_public, search_configured
from app.pulse.service import add_comment, add_manual, list_feed, set_status

router = APIRouter(prefix="/api/pulse")


@router.get("")
def get_feed(
    urgency: str | None = None,
    source_type: str | None = None,
    topic: str | None = None,
    status: str | None = "open",
    date_from: str | None = None,
    date_to: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(require_module("pulse")),
):
    feed = list_feed(
        db,
        urgency=urgency,
        source_type=source_type,
        topic=topic,
        status=status,
        date_from=date_from,
        date_to=date_to,
        query=q,
    )
    feed["sources"] = {"web_search": search_configured(db)}
    return feed


@router.post("/fetch")
def post_fetch(body: dict | None = None, db: Session = Depends(get_db), actor=Depends(require_module("pulse", manage=True))):
    payload = body or {}
    try:
        limit = int(payload.get("limit") or 8)
    except (TypeError, ValueError):
        limit = 8
    result = pull_public(db, actor, query=str(payload.get("query") or "") or None, limit=limit)
    record(
        db,
        user=actor,
        action="pulse_fetch",
        module="pulse",
        target=str(result.get("provider") or ""),
        detail={"created": result.get("created", 0), "provider": result.get("provider")},
    )
    db.commit()
    return result


@router.post("")
def post_item(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("pulse", manage=True))):
    return add_manual(db, actor, body)


@router.patch("/{item_id}")
def patch_item(item_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("pulse", manage=True))):
    return set_status(db, actor, item_id, str(body.get("status") or ""))


@router.post("/{item_id}/comments")
def post_comment(item_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("pulse", manage=True))):
    return add_comment(db, actor, item_id, str(body.get("body") or ""))
