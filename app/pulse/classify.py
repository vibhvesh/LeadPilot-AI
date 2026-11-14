"""Urgency and source type for an industry headline. No network calls."""

import re

URGENCIES = ("urgent", "week", "fyi")
URGENCY_LABELS = {"urgent": "Urgent", "week": "This week", "fyi": "FYI"}
SOURCE_TYPES = ("news", "forum", "social")
SOURCE_LABELS = {"news": "Web news", "forum": "Forum", "social": "Social discussion"}

_URGENCY_ALIASES = {
    "urgent": "urgent",
    "now": "urgent",
    "high": "urgent",
    "week": "week",
    "this week": "week",
    "thisweek": "week",
    "soon": "week",
    "fyi": "fyi",
    "info": "fyi",
    "context": "fyi",
    "later": "fyi",
}

_SOURCE_ALIASES = {
    "news": "news",
    "web": "news",
    "web news": "news",
    "article": "news",
    "forum": "forum",
    "message": "forum",
    "internet": "forum",
    "reddit": "forum",
    "social": "social",
    "discussion": "social",
    "x": "social",
    "linkedin": "social",
}

_URGENT = re.compile(
    r"("
    r"\burgent\b|effective immediately|takes effect|goes into effect|\bdeadline\b|"
    r"\bbanned\b|\bban on\b|cap reached|layoff|laid off|compliance|enforcement|"
    r"\bdebar|\bfraud alert\b|\bshutdown\b|"
    r"h-?1b (cap|lottery|fee|rule)|uscis .{0,48}(rule|fee|deadline|effective)"
    r")",
    re.IGNORECASE,
)

_WEEK = re.compile(
    r"("
    r"this week|this month|bill rates?|vendor management|\bvms\b|\bmsp\b|"
    r"hiring (trend|demand|slowdown|surge)|staffing (industry|demand|market)|"
    r"\bc2c\b|corp[- ]to[- ]corp|rate card"
    r")",
    re.IGNORECASE,
)


def normalize_urgency(value) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().lower().replace("_", " ").replace("-", " ").split())
    if not text:
        return None
    if text in _URGENCY_ALIASES:
        return _URGENCY_ALIASES[text]
    return _URGENCY_ALIASES.get(text.replace(" ", ""))


def normalize_source_type(value) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().lower().replace("_", " ").replace("-", " ").split())
    if not text:
        return None
    if text in _SOURCE_ALIASES:
        return _SOURCE_ALIASES[text]
    return _SOURCE_ALIASES.get(text.replace(" ", ""))


def classify_urgency(*parts: str) -> str:
    text = " ".join(part for part in parts if part).strip()
    if not text:
        return "fyi"
    if _URGENT.search(text):
        return "urgent"
    if _WEEK.search(text):
        return "week"
    return "fyi"


def why_it_matters(urgency: str, topic: str) -> str:
    subject = topic.strip() or "US IT staffing"
    if urgency == "urgent":
        return f"Time-sensitive for {subject}. It can change placements, work auth, or vendor programs now."
    if urgency == "week":
        return f"Worth a look this week for {subject}: hiring, rates, or how vendors are being managed."
    return f"Industry context on {subject}. No immediate action."
