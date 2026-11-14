"""Signed-in Social page API. Drafts stay in the app."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.database import get_db
from app.core.deps import require_module
from app.social.fetch import enrich_x_url, pull_public, source_flags
from app.social.service import add_comment, add_manual, list_feed, set_status

router = APIRouter(prefix="/api/social")


@router.get("")
def get_feed(
    platform: str | None = None,
    topic: str | None = None,
    company: str | None = None,
    status: str | None = "open",
    bucket: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(require_module("social")),
):
    feed = list_feed(
        db,
        platform=platform,
        topic=topic,
        company=company,
        status=status,
        bucket=bucket,
        date_from=date_from,
        date_to=date_to,
        query=q,
    )
    feed["sources"] = source_flags(db)
    return feed


@router.post("/fetch")
def post_fetch(body: dict | None = None, db: Session = Depends(get_db), actor=Depends(require_module("social", manage=True))):
    payload = body or {}
    try:
        limit = int(payload.get("limit") or 10)
    except (TypeError, ValueError):
        limit = 10
    result = pull_public(db, actor, query=str(payload.get("query") or "") or None, limit=limit)
    record(
        db,
        user=actor,
        action="social_fetch",
        module="social",
        target=str(result.get("provider") or ""),
        detail={"created": result.get("created", 0), "provider": result.get("provider")},
    )
    db.commit()
    return result


@router.post("")
def post_link(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("social", manage=True))):
    enriched = enrich_x_url(db, str(body.get("url") or body.get("post_url") or body.get("link") or ""))
    merged = dict(enriched)
    for key, value in body.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        merged[key] = value
    return add_manual(db, actor, merged)


@router.patch("/{item_id}")
def patch_item(item_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("social", manage=True))):
    return set_status(db, actor, item_id, str(body.get("status") or ""))


@router.post("/{item_id}/comments")
def post_comment(item_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("social", manage=True))):
    return add_comment(db, actor, item_id, str(body.get("body") or ""))
