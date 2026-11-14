"""Normalize public social links. This module never signs in or fetches a page."""

import hashlib
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.core.errors import AppError

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "si", "s"}
PLATFORMS = ("x", "linkedin", "facebook", "reddit", "job_board", "other")
PLATFORM_LABELS = {
    "x": "X",
    "linkedin": "LinkedIn",
    "facebook": "Facebook",
    "reddit": "Reddit",
    "job_board": "Job board",
    "other": "Other",
}
PLATFORM_ALIASES = {
    "x": "x",
    "twitter": "x",
    "tweet": "x",
    "linkedin": "linkedin",
    "li": "linkedin",
    "facebook": "facebook",
    "fb": "facebook",
    "meta": "facebook",
    "reddit": "reddit",
    "job_board": "job_board",
    "jobboard": "job_board",
    "job": "job_board",
    "jobs": "job_board",
    "indeed": "job_board",
    "dice": "job_board",
    "glassdoor": "job_board",
    "other": "other",
}
LOGIN_MARKERS = ("/login", "/checkpoint", "/uas/", "/authwall", "/signup", "/auth/", "/messaging")


def canonical_url(value: str) -> str:
    text = (value or "").strip()
    parsed = urlparse(text)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or "@" in parsed.netloc:
        raise AppError("Paste a public http(s) link")
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path or "/"
    if len(path) > 1:
        path = path.rstrip("/")
    query = urlencode(
        [(key, item) for key, item in parse_qsl(parsed.query, keep_blank_values=False) if key.lower() not in TRACKING_PARAMS]
    )
    url = urlunparse((parsed.scheme.lower(), host, path, "", query, ""))
    if len(url) > 1000:
        raise AppError("That link is too long")
    _reject_login_wall(url)
    return url


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _reject_login_wall(url: str) -> None:
    parsed = urlparse(url)
    path = parsed.path.lower()
    if any(marker in path for marker in LOGIN_MARKERS):
        if "linkedin.com" in parsed.netloc:
            raise AppError("Paste a public LinkedIn post. LeadPilot does not sign in to LinkedIn.")
        raise AppError("Paste a public post link. LeadPilot does not sign in to social accounts.")


def platform_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.endswith("x.com") or host.endswith("twitter.com") or host == "t.co":
        return "x"
    if host.endswith("linkedin.com"):
        return "linkedin"
    if host.endswith("facebook.com") or host.endswith("fb.com") or host.endswith("fb.me"):
        return "facebook"
    if host.endswith("reddit.com") or host == "redd.it":
        return "reddit"
    if any(host.endswith(name) for name in ("indeed.com", "dice.com", "glassdoor.com", "monster.com", "ziprecruiter.com")):
        return "job_board"
    return "other"


def normalize_platform(value: str | None, url: str) -> str:
    text = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if text in PLATFORM_ALIASES:
        return PLATFORM_ALIASES[text]
    return platform_from_url(url)


def x_status_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if not (host.endswith("x.com") or host.endswith("twitter.com")):
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 3 and parts[-2] == "status" and parts[-1].isdigit():
        return parts[-1]
    return None


def is_linkedin_public_post(url: str) -> bool:
    parsed = urlparse(url)
    if not parsed.netloc.endswith("linkedin.com"):
        return False
    path = parsed.path.lower()
    if any(marker in path for marker in LOGIN_MARKERS):
        return False
    return path.startswith("/posts") or path.startswith("/feed/update") or path.startswith("/pulse")


def is_fetchable_public_url(url: str) -> bool:
    """Search results worth saving. LinkedIn is limited to public post paths."""
    platform = platform_from_url(url)
    if platform == "linkedin":
        return is_linkedin_public_post(url)
    return platform != "other"


def slug(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in (value or "").strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")[:200]


def discussion_key(raw: dict, url: str, topic: str, company: str) -> str:
    explicit = str(raw.get("discussion_key") or raw.get("thread") or raw.get("conversation_id") or "").strip()
    if explicit:
        return slug(explicit) or slug(url) or "item"
    if company and topic:
        return slug(f"{company}-{topic}") or slug(url) or "item"
    if topic:
        return slug(topic) or slug(url) or "item"
    return slug(url) or "item"
