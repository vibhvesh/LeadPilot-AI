"""Decide Reply to / Engage / FYI and write a draft. Drafts are never sent."""

import re

BUCKETS = ("reply", "engage", "fyi")
BUCKET_LABELS = {"reply": "Reply to", "engage": "Engage", "fyi": "FYI"}

_ALIASES = {
    "reply": "reply",
    "reply to": "reply",
    "replyto": "reply",
    "respond": "reply",
    "engage": "engage",
    "comment": "engage",
    "like": "engage",
    "fyi": "fyi",
    "info": "fyi",
    "context": "fyi",
}

_REPLY = re.compile(
    r"("
    r"looking for (a |an )?(vendor|recruiter|agency|staffing|c2c|corp[- ]to[- ]corp|partner)s?"
    r"|need (a |an )?(vendor|recruiter|agency|c2c partner|staffing partner)s?"
    r"|seeking (a |an )?(vendor|recruiter|c2c|agency)s?"
    r"|open to (vendors|agencies|c2c|recruiters)"
    r"|vendors? (welcome|wanted|needed|please|dm)"
    r"|agencies welcome"
    r"|any recruiters"
    r"|anyone know (a |any )?(vendor|recruiter|agency|c2c)s?"
    r"|recruiters? for "
    r"|recruiters? (please|dm|ping|welcome)"
    r"|who can (staff|supply|provide) "
    r"|c2c (partners|vendors|ok|welcome|needed)"
    r"|looking for c2c"
    r"|implementation partners? (welcome|wanted|needed)"
    r")",
    re.IGNORECASE,
)

_ENGAGE = re.compile(
    r"("
    r"\b(c2c|h-?1b|w-?2|1099|corp[- ]to[- ]corp)\b"
    r"|staffing|recruiter|recruiting|bench sale|implementation partner"
    r"|contract (role|to hire|position)"
    r"|(hiring|open role|req).{0,48}(engineer|developer|architect|devops|salesforce|java|python|\.net|data)"
    r"|systems integrator"
    r")",
    re.IGNORECASE,
)

_AUTH = (
    ("C2C", re.compile(r"\b(c2c|corp[- ]to[- ]corp|corp2corp)\b", re.IGNORECASE)),
    ("H1B", re.compile(r"\bh-?1b\b", re.IGNORECASE)),
    ("W2", re.compile(r"\bw-?2\b", re.IGNORECASE)),
    ("1099", re.compile(r"\b1099\b", re.IGNORECASE)),
)


def normalize_bucket(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower().replace("_", " ").replace("-", " ")
    text = " ".join(text.split())
    if not text:
        return None
    if text in _ALIASES:
        return _ALIASES[text]
    compact = text.replace(" ", "")
    return _ALIASES.get(compact)


def work_auth_terms(*parts: str) -> str:
    text = " ".join(part for part in parts if part)
    return ", ".join(label for label, pattern in _AUTH if pattern.search(text))


def classify_bucket(*parts: str) -> str:
    text = " ".join(part for part in parts if part).strip()
    if not text:
        return "fyi"
    if _REPLY.search(text):
        return "reply"
    if _ENGAGE.search(text):
        return "engage"
    return "fyi"


def why_it_matters(bucket: str, company: str, work_auth: str) -> str:
    firm = company.strip() or "A US company or IT services firm"
    auth = f" Work auth mentioned: {work_auth}." if work_auth else ""
    if bucket == "reply":
        return f"{firm} is asking for a vendor, recruiter, or C2C partner.{auth}"
    if bucket == "engage":
        return f"Relevant hiring or work-authorization discussion involving {firm}.{auth}"
    return f"Context only. Worth keeping, with no reply needed.{auth}"


def draft_reply(bucket: str, *, poster_name: str, company: str, work_auth: str) -> str:
    if bucket == "fyi":
        return ""
    who = poster_name.strip() or "there"
    firm = company.strip() or "your team"
    auth = work_auth.strip() or "C2C or W2"
    if bucket == "reply":
        return (
            f"Hi {who} — we staff US-based IT roles for companies and systems integrators, "
            f"and we can work {auth}. If {firm} is still looking for a vendor partner, "
            f"I can send two or three people who match the req. Happy to share details here."
        )
    return (
        f"Hi {who} — we help US companies and IT SIs fill onshore IT roles ({auth}) "
        f"and we only step in when a req is open to vendors. If {firm} is hiring, "
        f"I can compare notes or send a short list."
    )
