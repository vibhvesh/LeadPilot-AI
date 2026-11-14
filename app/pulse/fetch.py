"""Optional read of public news and discussions. Never posts and never signs in."""

from app.core.errors import AppError
from app.pulse.classify import classify_urgency
from app.pulse.links import resolve_source_type
from app.search.providers import choose_search_provider, search_documents
from app.pulse.service import ingest_items
from app.social.links import canonical_url

DEFAULT_QUERY = (
    '("IT staffing" OR "H-1B" OR H1B OR "vendor management" OR C2C OR "corp to corp") '
    '(USCIS OR hiring OR recruiting OR "staffing industry" OR "bill rate")'
)


def search_configured(db) -> bool:
    try:
        choose_search_provider(db)
    except AppError:
        return False
    return True


def pull_public(db, actor, query: str | None = None, limit: int = 8) -> dict:
    if not search_configured(db):
        raise AppError("No search key is configured. Add a Tavily or Brave key under API keys, or paste a story.")
    bounded = max(1, min(int(limit or 8), 8))
    provider, documents = search_documents(db, (query or DEFAULT_QUERY).strip(), bounded)
    items = [item for item in (_from_document(document) for document in documents) if item]
    if not items:
        return {
            "provider": provider,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "items": [],
            "note": "No public stories matched. Nothing was posted.",
        }
    result = ingest_items(db, items, origin="web_search", actor=actor)
    result["provider"] = provider
    result["note"] = "Saved public stories from web search. Nothing was posted."
    return result


def _from_document(document: dict) -> dict | None:
    raw_url = str(document.get("url") or "").strip()
    title = str(document.get("title") or "").strip()
    snippet = str(document.get("snippet") or "").strip()
    if not raw_url or len(title) < 4:
        return None
    try:
        url = canonical_url(raw_url)
    except AppError:
        return None
    why = snippet[:400] or None
    return {
        "headline": title[:300],
        "url": url,
        "why_it_matters": why or "",
        "source_type": resolve_source_type(None, url),
        "urgency": classify_urgency(title, snippet),
        "topic": _topic(title, snippet),
    }


def _topic(title: str, snippet: str) -> str:
    text = f"{title} {snippet}".lower()
    if "h-1b" in text or "h1b" in text:
        return "H-1B policy"
    if "c2c" in text or "corp to corp" in text or "corp-to-corp" in text:
        return "C2C"
    if "vendor management" in text or " vms" in f" {text}" or "msp" in text:
        return "Vendor management"
    if "hiring" in text or "layoff" in text:
        return "Hiring trends"
    return "US IT staffing"
