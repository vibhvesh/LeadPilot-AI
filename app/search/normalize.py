"""Normalize company records and build stable deduplication keys."""

import re
from urllib.parse import urlparse

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}")

DIRECTORY_HOSTS = (
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "wikipedia.org",
    "crunchbase.com",
    "google.com",
    "bing.com",
    "yelp.com",
)


def hostname(url: str) -> str:
    if not url:
        return ""
    candidate = url if "://" in url else "https://" + url
    host = (urlparse(candidate).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def is_directory_host(url: str) -> bool:
    host = hostname(url)
    return any(host == domain or host.endswith("." + domain) for domain in DIRECTORY_HOSTS)


def company_website(url: str) -> str:
    if not url or is_directory_host(url):
        return ""
    return url.strip()


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def dedup_key(company: str, website: str = "") -> str:
    host = hostname(website)
    if host and not is_directory_host(website):
        return f"domain:{host}"[:300]
    name = normalize_name(company)
    return f"name:{name or 'unknown'}"[:300]


def clean_title(title: str) -> str:
    text = re.split(r"\s[\|\-–—:]\s", title or "")[0]
    text = re.sub(r"\b(LinkedIn|Crunchbase|Wikipedia|Facebook|Home|Official)\b", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" -|")
    return text or (title or "").strip()


def extract_email(text: str) -> str:
    match = EMAIL_RE.search(text or "")
    if not match:
        return ""
    email = match.group(0).strip().lower()
    if email.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
        return ""
    return email


def extract_phone(text: str) -> str:
    for match in PHONE_RE.finditer(text or ""):
        raw = match.group(0).strip()
        digits = re.sub(r"\D", "", raw)
        if 10 <= len(digits) <= 15:
            return raw
    return ""


def split_keywords(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,;/|]", value or "") if len(part.strip()) > 1]
