"""Turn a headline and its links into a pulse card."""

from urllib.parse import urlparse

from app.core.errors import AppError
from app.pulse.classify import normalize_source_type
from app.social.links import canonical_url

_FORUM_HOSTS = ("reddit.com", "redd.it", "news.ycombinator.com", "teamblind.com", "fishbowlapp.com")
_SOCIAL_HOSTS = ("x.com", "twitter.com", "t.co", "linkedin.com", "facebook.com", "fb.com", "fb.me")


def source_type_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if any(host.endswith(name) for name in _FORUM_HOSTS):
        return "forum"
    if any(host.endswith(name) for name in _SOCIAL_HOSTS):
        return "social"
    return "news"


def resolve_source_type(value: str | None, url: str) -> str:
    explicit = normalize_source_type(value)
    if explicit:
        return explicit
    return source_type_from_url(url)


def collect_links(raw: dict) -> list[str]:
    primary_raw = str(raw.get("url") or raw.get("source_url") or raw.get("link") or "").strip()
    if not primary_raw:
        raise AppError("A public source link is required")
    primary = canonical_url(primary_raw)
    extras = []
    provided = raw.get("links") if "links" in raw else raw.get("sources")
    if isinstance(provided, str):
        provided = [part.strip() for part in provided.replace("\n", ",").split(",") if part.strip()]
    if isinstance(provided, list):
        for item in provided:
            if isinstance(item, str):
                candidate = item
            elif isinstance(item, dict):
                candidate = str(item.get("url") or item.get("link") or "")
            else:
                continue
            if not candidate.strip():
                continue
            try:
                extras.append(canonical_url(candidate))
            except AppError:
                continue
    ordered = []
    for url in [primary, *extras]:
        if url not in ordered:
            ordered.append(url)
    return ordered[:8]
