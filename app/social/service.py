"""Store, list, and update social feed items. Callers commit."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.errors import AppError
from app.models.social import SOCIAL_STATUSES, SocialComment, SocialItem
from app.models import User
from app.social.classify import (
    BUCKET_LABELS,
    classify_bucket,
    draft_reply,
    normalize_bucket,
    why_it_matters,
    work_auth_terms,
)
from app.social.links import (
    PLATFORM_LABELS,
    canonical_url,
    discussion_key,
    normalize_platform,
    url_hash,
)

MAX_ITEMS = 50
LIST_LIMIT = 200


def ingest_items(db: Session, items, *, source: str, actor=None, token=None, request_id=None) -> dict:
    if not isinstance(items, list) or not items:
        raise AppError("Send at least one social item")
    if len(items) > MAX_ITEMS:
        raise AppError("Send at most 50 social items at a time")
    created = updated = skipped = 0
    saved = []
    for raw in items:
        if not isinstance(raw, dict):
            skipped += 1
            continue
        try:
            row, outcome = upsert_item(db, raw, source=source, actor_id=getattr(actor, "id", None))
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
        action="social_ingest",
        module="social",
        target=str(request_id or ""),
        detail={
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "source": source,
            "token_id": getattr(token, "id", None),
            "request_id": request_id,
        },
    )
    db.commit()
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "items": [serialize_item(row, _comments_for(db, [row.id]).get(row.id, [])) for row in saved],
    }


def add_manual(db: Session, actor, raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise AppError("Send the public link as JSON")
    row, outcome = upsert_item(db, raw, source="manual", actor_id=actor.id)
    if outcome == "skipped":
        raise AppError("Paste a public http(s) link")
    record(
        db,
        user=actor,
        action="social_ingest",
        module="social",
        target=str(row.id),
        detail={"source": "manual", "outcome": outcome, "platform": row.platform},
    )
    db.commit()
    db.refresh(row)
    return serialize_item(row, _comments_for(db, [row.id]).get(row.id, []))


def list_feed(
    db: Session,
    *,
    platform: str | None = None,
    topic: str | None = None,
    company: str | None = None,
    status: str | None = "open",
    bucket: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    query: str | None = None,
    limit: int = LIST_LIMIT,
) -> dict:
    statement = select(SocialItem)
    status_value = (status or "open").strip().lower()
    if status_value != "all":
        if status_value not in SOCIAL_STATUSES:
            raise AppError("Status must be open, done, ignored, or all")
        statement = statement.where(SocialItem.status == status_value)
    if platform and platform.strip():
        platform_value = normalize_platform(platform, "")
        token = platform.strip().lower().replace("-", "_").replace(" ", "_")
        if platform_value == "other" and token not in {"other"}:
            raise AppError("Unknown platform")
        statement = statement.where(SocialItem.platform == platform_value)
    if bucket:
        bucket_value = normalize_bucket(bucket)
        if bucket_value is None:
            raise AppError("Bucket must be reply, engage, or fyi")
        statement = statement.where(SocialItem.bucket == bucket_value)
    if topic and topic.strip():
        statement = statement.where(SocialItem.topic.ilike(_like(topic)))
    if company and company.strip():
        statement = statement.where(SocialItem.company.ilike(_like(company)))
    if query and query.strip():
        like = _like(query)
        statement = statement.where(
            or_(
                SocialItem.snippet.ilike(like),
                SocialItem.poster_name.ilike(like),
                SocialItem.topic.ilike(like),
                SocialItem.company.ilike(like),
                SocialItem.why_it_matters.ilike(like),
            )
        )
    stamp = func.coalesce(SocialItem.posted_at, SocialItem.created_at)
    start = _day_bound(date_from, end=False)
    end = _day_bound(date_to, end=True)
    if start is not None:
        statement = statement.where(stamp >= start)
    if end is not None:
        statement = statement.where(stamp < end)
    bounded = max(1, min(int(limit or LIST_LIMIT), LIST_LIMIT))
    statement = statement.order_by(SocialItem.posted_at.is_(None), SocialItem.posted_at.desc(), SocialItem.id.desc()).limit(bounded)
    rows = db.scalars(statement).all()
    comments = _comments_for(db, [row.id for row in rows])
    items = [serialize_item(row, comments.get(row.id, [])) for row in rows]
    counts = {"reply": 0, "engage": 0, "fyi": 0, "open": 0, "done": 0, "ignored": 0}
    for item in items:
        counts[item["bucket"]] = counts.get(item["bucket"], 0) + 1
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return {"items": items, "groups": group_items(items), "counts": counts}


def list_for_bot(db: Session, status: str | None = None) -> dict:
    """Include done and ignored items so a bot can learn which posts the team acted on."""
    return list_feed(db, status=status or "all")


def set_status(db: Session, actor, item_id: int, status: str) -> dict:
    value = (status or "").strip().lower()
    if value not in SOCIAL_STATUSES:
        raise AppError("Status must be open, done, or ignored")
    row = _get(db, item_id)
    row.status = value
    record(db, user=actor, action="social_status", module="social", target=str(row.id), detail={"status": value})
    db.commit()
    db.refresh(row)
    return serialize_item(row, _comments_for(db, [row.id]).get(row.id, []))


def add_comment(db: Session, actor, item_id: int, body: str) -> dict:
    text = (body or "").strip()
    if not text:
        raise AppError("Write a comment before posting")
    row = _get(db, item_id)
    comment = SocialComment(item_id=row.id, author_id=actor.id, body=text[:4000])
    db.add(comment)
    db.flush()
    record(db, user=actor, action="social_comment", module="social", target=str(row.id), detail={"comment_id": comment.id})
    db.commit()
    db.refresh(row)
    return serialize_item(row, _comments_for(db, [row.id]).get(row.id, []))


def upsert_item(db: Session, raw: dict, *, source: str, actor_id: int | None) -> tuple[SocialItem, str]:
    prepared = prepare_item(raw)
    existing = db.scalar(select(SocialItem).where(SocialItem.url_hash == prepared["url_hash"]))
    if existing is not None:
        _apply_update(existing, raw, prepared)
        return existing, "updated"
    row = SocialItem(
        platform=prepared["platform"],
        post_url=prepared["post_url"],
        url_hash=prepared["url_hash"],
        poster_name=prepared["poster_name"],
        poster_role=prepared["poster_role"],
        posted_at=prepared["posted_at"],
        snippet=prepared["snippet"],
        topic=prepared["topic"],
        company=prepared["company"],
        discussion_key=prepared["discussion_key"],
        bucket=prepared["bucket"],
        why_it_matters=prepared["why_it_matters"],
        suggested_reply=prepared["suggested_reply"],
        work_auth=prepared["work_auth"],
        status="open",
        source=(source or "manual")[:40],
        created_by=actor_id,
    )
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        existing = db.scalar(select(SocialItem).where(SocialItem.url_hash == prepared["url_hash"]))
        if existing is None:
            return row, "skipped"
        _apply_update(existing, raw, prepared)
        return existing, "updated"
    return row, "created"


def prepare_item(raw: dict) -> dict:
    url = canonical_url(str(raw.get("url") or raw.get("post_url") or raw.get("link") or ""))
    platform = normalize_platform(str(raw.get("platform") or raw.get("source_platform") or ""), url)
    snippet = _clip(raw.get("snippet") or raw.get("quote") or raw.get("summary") or raw.get("text") or "", 4000)
    topic = _clip(raw.get("topic") or "", 200)
    company = _clip(raw.get("company") or raw.get("related_company") or "", 250)
    poster_name = _clip(raw.get("poster_name") or raw.get("poster") or raw.get("author") or "", 250)
    poster_role = _clip(raw.get("poster_role") or raw.get("role") or "", 250)
    posted_at = parse_when(raw.get("posted_at") if "posted_at" in raw else raw.get("date"))
    supplied_auth = _clip(raw.get("work_auth") or raw.get("work_authorization") or "", 80) if _present(raw, "work_auth", "work_authorization") else ""
    work_auth = supplied_auth or work_auth_terms(snippet, topic)
    explicit_bucket = normalize_bucket(raw.get("bucket") if "bucket" in raw else raw.get("classification") if "classification" in raw else raw.get("section"))
    bucket = explicit_bucket or classify_bucket(snippet, topic, str(raw.get("why_it_matters") or raw.get("why") or ""))
    if _present(raw, "why_it_matters", "why"):
        why = _clip(raw.get("why_it_matters") or raw.get("why") or "", 2000)
    else:
        why = why_it_matters(bucket, company, work_auth)
    if _present(raw, "suggested_reply", "reply_draft", "draft"):
        reply = _clip(raw.get("suggested_reply") or raw.get("reply_draft") or raw.get("draft") or "", 4000)
    else:
        reply = draft_reply(bucket, poster_name=poster_name, company=company, work_auth=work_auth)
    return {
        "platform": platform,
        "post_url": url,
        "url_hash": url_hash(url),
        "poster_name": poster_name,
        "poster_role": poster_role,
        "posted_at": posted_at,
        "snippet": snippet,
        "topic": topic,
        "company": company,
        "discussion_key": discussion_key(raw, url, topic, company),
        "bucket": bucket,
        "why_it_matters": why,
        "suggested_reply": reply,
        "work_auth": work_auth[:80],
    }


def serialize_item(item: SocialItem, comments: list[dict] | None = None) -> dict:
    return {
        "id": item.id,
        "platform": item.platform,
        "platform_label": PLATFORM_LABELS.get(item.platform, item.platform),
        "url": item.post_url,
        "poster_name": item.poster_name or "",
        "poster_role": item.poster_role or "",
        "posted_at": item.posted_at.isoformat() if item.posted_at else None,
        "snippet": item.snippet or "",
        "topic": item.topic or "",
        "company": item.company or "",
        "discussion_key": item.discussion_key or "",
        "bucket": item.bucket,
        "bucket_label": BUCKET_LABELS.get(item.bucket, item.bucket),
        "why_it_matters": item.why_it_matters or "",
        "suggested_reply": item.suggested_reply or "",
        "work_auth": item.work_auth or "",
        "status": item.status,
        "source": item.source or "",
        "comments": comments or [],
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def group_items(items: list[dict]) -> list[dict]:
    order: list[str] = []
    groups: dict[str, dict] = {}
    for item in items:
        key = item.get("discussion_key") or f"item-{item['id']}"
        if key not in groups:
            groups[key] = {
                "discussion_key": key,
                "topic": item.get("topic") or "",
                "company": item.get("company") or "",
                "item_ids": [],
            }
            order.append(key)
        group = groups[key]
        group["item_ids"].append(item["id"])
        if not group["topic"] and item.get("topic"):
            group["topic"] = item["topic"]
        if not group["company"] and item.get("company"):
            group["company"] = item["company"]
    return [groups[key] for key in order]


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


def _apply_update(existing: SocialItem, raw: dict, prepared: dict) -> None:
    snippet_changed = bool(prepared["snippet"]) and prepared["snippet"] != (existing.snippet or "")
    for field in ("platform", "poster_name", "poster_role", "snippet", "topic", "company", "work_auth", "discussion_key"):
        if prepared[field]:
            setattr(existing, field, prepared[field])
    if prepared["posted_at"] is not None:
        existing.posted_at = prepared["posted_at"]
    if _explicit_bucket(raw) is not None or snippet_changed:
        existing.bucket = prepared["bucket"]
    if _present(raw, "why_it_matters", "why") or snippet_changed or _explicit_bucket(raw) is not None:
        if _present(raw, "why_it_matters", "why") or snippet_changed or not existing.why_it_matters:
            existing.why_it_matters = prepared["why_it_matters"]
    if _present(raw, "suggested_reply", "reply_draft", "draft") or (snippet_changed and not _present(raw, "suggested_reply", "reply_draft", "draft")):
        existing.suggested_reply = prepared["suggested_reply"]
    existing.post_url = prepared["post_url"]


def _explicit_bucket(raw: dict):
    if "bucket" in raw:
        return normalize_bucket(raw.get("bucket"))
    if "classification" in raw:
        return normalize_bucket(raw.get("classification"))
    if "section" in raw:
        return normalize_bucket(raw.get("section"))
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


def _get(db: Session, item_id: int) -> SocialItem:
    row = db.get(SocialItem, item_id)
    if row is None:
        raise AppError("Social item not found", 404)
    return row


def _comments_for(db: Session, ids: list[int]) -> dict[int, list[dict]]:
    if not ids:
        return {}
    rows = db.scalars(select(SocialComment).where(SocialComment.item_id.in_(ids)).order_by(SocialComment.id.asc())).all()
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
