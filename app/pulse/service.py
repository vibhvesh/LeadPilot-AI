"""Store and list Industry Pulse cards. Callers commit."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.errors import AppError
from app.models import User
from app.models.pulse import PULSE_STATUSES, PulseComment, PulseItem
from app.pulse.classify import (
    SOURCE_LABELS,
    URGENCY_LABELS,
    classify_urgency,
    normalize_urgency,
    why_it_matters,
)
from app.pulse.links import collect_links, resolve_source_type
from app.social.links import url_hash

MAX_ITEMS = 50
LIST_LIMIT = 200
_URGENCY_RANK = case((PulseItem.urgency == "urgent", 0), (PulseItem.urgency == "week", 1), else_=2)


def ingest_items(db: Session, items, *, origin: str, actor=None, token=None) -> dict:
    if not isinstance(items, list) or not items:
        raise AppError("Send at least one pulse item")
    if len(items) > MAX_ITEMS:
        raise AppError("Send at most 50 pulse items at a time")
    created = updated = skipped = 0
    saved = []
    for raw in items:
        if not isinstance(raw, dict):
            skipped += 1
            continue
        try:
            row, outcome = upsert_item(db, raw, origin=origin, actor_id=getattr(actor, "id", None))
        except AppError:
            skipped += 1
            continue
        if outcome == "created":
            created += 1
        elif outcome == "updated":
            updated += 1
        else:
            skipped += 1
            continue
        saved.append(row)
    record(
        db,
        user=actor,
        email="" if actor is not None else f"bot:{getattr(token, 'name', '')}",
        action="pulse_ingest",
        module="pulse",
        detail={
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "origin": origin,
            "token_id": getattr(token, "id", None),
        },
    )
    db.commit()
    comments = _comments_for(db, [row.id for row in saved])
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "items": [serialize_item(row, comments.get(row.id, [])) for row in saved],
    }


def add_manual(db: Session, actor, raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise AppError("Send the headline as JSON")
    row, outcome = upsert_item(db, raw, origin="manual", actor_id=actor.id)
    if outcome == "skipped":
        raise AppError("A headline and a public source link are required")
    record(
        db,
        user=actor,
        action="pulse_ingest",
        module="pulse",
        target=str(row.id),
        detail={"origin": "manual", "outcome": outcome, "urgency": row.urgency},
    )
    db.commit()
    db.refresh(row)
    return serialize_item(row, _comments_for(db, [row.id]).get(row.id, []))


def list_feed(
    db: Session,
    *,
    urgency: str | None = None,
    source_type: str | None = None,
    topic: str | None = None,
    status: str | None = "open",
    date_from: str | None = None,
    date_to: str | None = None,
    query: str | None = None,
    limit: int = LIST_LIMIT,
) -> dict:
    statement = select(PulseItem)
    status_value = (status or "open").strip().lower()
    if status_value != "all":
        if status_value not in PULSE_STATUSES:
            raise AppError("Status must be open, read, dismissed, or all")
        statement = statement.where(PulseItem.status == status_value)
    if urgency and urgency.strip():
        urgency_value = normalize_urgency(urgency)
        if urgency_value is None:
            raise AppError("Urgency must be urgent, week, or fyi")
        statement = statement.where(PulseItem.urgency == urgency_value)
    if source_type and source_type.strip():
        token = " ".join(source_type.strip().lower().replace("-", " ").replace("_", " ").split())
        known = {
            "news",
            "web",
            "web news",
            "article",
            "forum",
            "message",
            "internet",
            "reddit",
            "social",
            "discussion",
            "x",
            "linkedin",
        }
        if token not in known:
            raise AppError("Unknown source type")
        statement = statement.where(PulseItem.source_type == resolve_source_type(token, ""))
    if topic and topic.strip():
        statement = statement.where(PulseItem.topic.ilike(_like(topic)))
    if query and query.strip():
        like = _like(query)
        statement = statement.where(
            or_(
                PulseItem.headline.ilike(like),
                PulseItem.why_it_matters.ilike(like),
                PulseItem.topic.ilike(like),
            )
        )
    stamp = func.coalesce(PulseItem.published_at, PulseItem.created_at)
    start = _day_bound(date_from, end=False)
    end = _day_bound(date_to, end=True)
    if start is not None:
        statement = statement.where(stamp >= start)
    if end is not None:
        statement = statement.where(stamp < end)
    bounded = max(1, min(int(limit or LIST_LIMIT), LIST_LIMIT))
    statement = statement.order_by(
        _URGENCY_RANK,
        PulseItem.published_at.is_(None),
        PulseItem.published_at.desc(),
        PulseItem.id.desc(),
    ).limit(bounded)
    rows = db.scalars(statement).all()
    comments = _comments_for(db, [row.id for row in rows])
    items = [serialize_item(row, comments.get(row.id, [])) for row in rows]
    counts = {"urgent": 0, "week": 0, "fyi": 0, "open": 0, "read": 0, "dismissed": 0}
    for item in items:
        counts[item["urgency"]] = counts.get(item["urgency"], 0) + 1
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return {"items": items, "counts": counts}


def list_for_bot(db: Session, status: str | None = None) -> dict:
    """Include read and dismissed cards so a bot can learn what the team wants."""
    return list_feed(db, status=status or "all")


def set_status(db: Session, actor, item_id: int, status: str) -> dict:
    value = (status or "").strip().lower()
    if value not in PULSE_STATUSES:
        raise AppError("Status must be open, read, or dismissed")
    row = _get(db, item_id)
    row.status = value
    record(db, user=actor, action="pulse_status", module="pulse", target=str(row.id), detail={"status": value})
    db.commit()
    db.refresh(row)
    return serialize_item(row, _comments_for(db, [row.id]).get(row.id, []))


def add_comment(db: Session, actor, item_id: int, body: str) -> dict:
    text = (body or "").strip()
    if not text:
        raise AppError("Write a comment before posting")
    row = _get(db, item_id)
    comment = PulseComment(item_id=row.id, author_id=actor.id, body=text[:4000])
    db.add(comment)
    db.flush()
    record(db, user=actor, action="pulse_comment", module="pulse", target=str(row.id), detail={"comment_id": comment.id})
    db.commit()
    db.refresh(row)
    return serialize_item(row, _comments_for(db, [row.id]).get(row.id, []))


def upsert_item(db: Session, raw: dict, *, origin: str, actor_id: int | None) -> tuple[PulseItem, str]:
    prepared = prepare_item(raw)
    existing = db.scalar(select(PulseItem).where(PulseItem.url_hash == prepared["url_hash"]))
    if existing is not None:
        _apply_update(existing, raw, prepared)
        return existing, "updated"
    row = PulseItem(
        headline=prepared["headline"],
        why_it_matters=prepared["why_it_matters"],
        urgency=prepared["urgency"],
        source_type=prepared["source_type"],
        source_url=prepared["source_url"],
        url_hash=prepared["url_hash"],
        links=prepared["links"],
        topic=prepared["topic"],
        published_at=prepared["published_at"],
        status="open",
        origin=(origin or "manual")[:40],
        created_by=actor_id,
    )
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        existing = db.scalar(select(PulseItem).where(PulseItem.url_hash == prepared["url_hash"]))
        if existing is None:
            return row, "skipped"
        _apply_update(existing, raw, prepared)
        return existing, "updated"
    return row, "created"


def prepare_item(raw: dict) -> dict:
    links = collect_links(raw)
    url = links[0]
    headline = _clip(raw.get("headline") or raw.get("title") or "", 300)
    if len(headline) < 4:
        raise AppError("A headline is required")
    topic = _clip(raw.get("topic") or "", 200)
    explicit_urgency = _explicit_urgency(raw)
    urgency = explicit_urgency or classify_urgency(headline, str(raw.get("why_it_matters") or raw.get("why") or ""), topic)
    if _present(raw, "why_it_matters", "why", "summary"):
        why = _clip(raw.get("why_it_matters") or raw.get("why") or raw.get("summary") or "", 400)
    else:
        why = why_it_matters(urgency, topic or headline)
    source_type = resolve_source_type(str(raw.get("source_type") or raw.get("source") or ""), url)
    published_at = parse_when(raw.get("published_at") if "published_at" in raw else raw.get("date"))
    return {
        "headline": headline,
        "why_it_matters": why,
        "urgency": urgency,
        "source_type": source_type,
        "source_url": url,
        "url_hash": url_hash(url),
        "links": links,
        "topic": topic,
        "published_at": published_at,
    }


def serialize_item(item: PulseItem, comments: list[dict] | None = None) -> dict:
    links = [link for link in (item.links or []) if isinstance(link, str)]
    if item.source_url and item.source_url not in links:
        links = [item.source_url, *links]
    return {
        "id": item.id,
        "headline": item.headline or "",
        "why_it_matters": item.why_it_matters or "",
        "urgency": item.urgency,
        "urgency_label": URGENCY_LABELS.get(item.urgency, item.urgency),
        "source_type": item.source_type,
        "source_label": SOURCE_LABELS.get(item.source_type, item.source_type),
        "url": item.source_url or "",
        "links": links,
        "topic": item.topic or "",
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "status": item.status,
        "origin": item.origin or "",
        "comments": comments or [],
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def parse_when(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _apply_update(existing: PulseItem, raw: dict, prepared: dict) -> None:
    headline_changed = prepared["headline"] != (existing.headline or "")
    existing.headline = prepared["headline"]
    existing.source_url = prepared["source_url"]
    if "links" in raw or "sources" in raw:
        existing.links = prepared["links"]
    else:
        current = [link for link in (existing.links or []) if isinstance(link, str)]
        merged = []
        for url in [prepared["source_url"], *current]:
            if url not in merged:
                merged.append(url)
        existing.links = merged[:8]
    if prepared["topic"]:
        existing.topic = prepared["topic"]
    if prepared["published_at"] is not None:
        existing.published_at = prepared["published_at"]
    existing.source_type = prepared["source_type"]
    if _explicit_urgency(raw) is not None or headline_changed:
        existing.urgency = prepared["urgency"]
    if _present(raw, "why_it_matters", "why", "summary") or headline_changed or not existing.why_it_matters:
        existing.why_it_matters = prepared["why_it_matters"]


def _explicit_urgency(raw: dict):
    if "urgency" in raw:
        return normalize_urgency(raw.get("urgency"))
    return None


def _present(raw: dict, *keys: str) -> bool:
    return any(key in raw and str(raw.get(key) or "").strip() for key in keys)


def _clip(value, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _like(value: str) -> str:
    return f"%{value.strip()}%"


def _day_bound(value: str | None, *, end: bool) -> datetime | None:
    if value is None or not str(value).strip():
        return None
    parsed = parse_when(value)
    if parsed is None:
        raise AppError("Use a YYYY-MM-DD date")
    start = parsed.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if end:
        return start + timedelta(days=1)
    return start


def _get(db: Session, item_id: int) -> PulseItem:
    row = db.get(PulseItem, item_id)
    if row is None:
        raise AppError("Pulse item not found", 404)
    return row


def _comments_for(db: Session, ids: list[int]) -> dict[int, list[dict]]:
    if not ids:
        return {}
    rows = db.scalars(select(PulseComment).where(PulseComment.item_id.in_(ids)).order_by(PulseComment.id.asc())).all()
    author_ids = {row.author_id for row in rows}
    authors = {}
    if author_ids:
        users = db.scalars(select(User).where(User.id.in_(author_ids))).all()
        authors = {user.id: user for user in users}
    grouped: dict[int, list[dict]] = {}
    for row in rows:
        author = authors.get(row.author_id)
        grouped.setdefault(row.item_id, []).append(
            {
                "id": row.id,
                "body": row.body,
                "author_name": author.display_name if author else "",
                "author_email": author.email if author else "",
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    return grouped
