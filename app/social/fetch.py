"""Optional read of public posts. Never posts and never signs in to a social account."""

from app.core.config import get_settings
from app.core.errors import AppError
from app.providers.secrets import resolve_secret
from app.search.providers import choose_search_provider, search_documents
from app.social.links import canonical_url, is_fetchable_public_url, platform_from_url, x_status_id
from app.social.service import ingest_items
from app.social.x_api import lookup_post, search_recent

DEFAULT_X_QUERY = (
    '("C2C" OR "corp to corp" OR "looking for vendors" OR "open to vendors" OR H1B OR "H-1B") '
    "(hiring OR recruiter OR staffing OR vendor) lang:en -is:retweet"
)
DEFAULT_WEB_QUERY = (
    '("C2C" OR "looking for vendors" OR "open to recruiters" OR H1B) '
    "(hiring OR staffing) (site:x.com OR site:twitter.com OR site:linkedin.com/posts OR site:reddit.com)"
)


def x_bearer(db) -> str | None:
    return resolve_secret(db, "x", get_settings().x_api_key)


def x_configured(db) -> bool:
    return bool(x_bearer(db))


def search_configured(db) -> bool:
    try:
        choose_search_provider(db)
    except AppError:
        return False
    return True


def source_flags(db) -> dict:
    return {"x_api": x_configured(db), "web_search": search_configured(db)}


def enrich_x_url(db, url: str) -> dict:
    """Fill a pasted X status from the public API when a key exists. Failures stay empty."""
    token = x_bearer(db)
    status_id = x_status_id(url or "")
    if not token or not status_id:
        return {}
    try:
        return lookup_post(token, status_id) or {}
    except AppError:
        return {}


def pull_public(db, actor, query: str | None = None, limit: int = 10) -> dict:
    bounded = max(1, min(int(limit or 10), 10))
    if x_configured(db):
        posts = search_recent(x_bearer(db) or "", (query or DEFAULT_X_QUERY).strip(), bounded)
        return _finish(db, actor, posts, source="x_api", provider="x", note="Read public posts from the X API. Nothing was posted.")
    if search_configured(db):
        provider, documents = search_documents(db, (query or DEFAULT_WEB_QUERY).strip(), bounded)
        posts = [item for item in (_from_document(document) for document in documents) if item]
        return _finish(
            db,
            actor,
            posts,
            source="web_search",
            provider=provider,
            note="Saved public links from web search. Nothing was posted or signed in to.",
        )
    raise AppError("No X API key or search key is configured. Add one under API keys, or paste a public link.")


def _finish(db, actor, posts: list, *, source: str, provider: str, note: str) -> dict:
    if not posts:
        return {"provider": provider, "created": 0, "updated": 0, "skipped": 0, "items": [], "note": "No public posts matched. Nothing was posted."}
    result = ingest_items(db, posts, source=source, actor=actor)
    result["provider"] = provider
    result["note"] = note
    return result


def _from_document(document: dict) -> dict | None:
    raw_url = str(document.get("url") or "").strip()
    if not raw_url:
        return None
    try:
        url = canonical_url(raw_url)
    except AppError:
        return None
    if not is_fetchable_public_url(url):
        return None
    snippet = str(document.get("snippet") or document.get("title") or "").strip()
    if not snippet:
        return None
    return {
        "platform": platform_from_url(url),
        "url": url,
        "snippet": snippet[:4000],
        "topic": "US IT vendor hiring",
        "discussion_key": url,
    }
