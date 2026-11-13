"""Specialist agents. Outreach produces a draft and never sends mail."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Lead
from app.search.normalize import extract_email, extract_phone
from app.settings.profile import profile_brief

SYSTEM = (
    "You are a sales research assistant for CanberraAI LeadPilot. "
    "Return only a JSON object. Do not include markdown. Never claim an email was sent."
)


def orchestrate(lead: Lead) -> dict:
    return {
        "agent": "orchestrator",
        "title": "Head Thinker / Orchestrator",
        "summary": f"Route {lead.company} through research, enrichment, quality, qualification, and outreach drafting.",
        "output": {
            "plan": ["research", "enrichment", "quality", "qualification", "outreach"],
            "human_review_required": True,
        },
    }


def research(lead: Lead, llm, profile: dict | None = None) -> dict:
    snippet = (lead.raw_payload or {}).get("snippet") or lead.notes or ""
    result = llm.complete_json(
        purpose="company_research",
        system=SYSTEM,
        prompt=(
            "Summarize this company for our sales team. JSON keys: summary (string), signals (array of short strings).\n"
            f"{profile_brief(profile)}\n"
            f"Company: {lead.company}\nIndustry: {lead.industry}\nLocation: {lead.city}, {lead.state}, {lead.country}\n"
            f"Website: {lead.website}\nNotes: {snippet}"
        ),
    )
    data = result["data"] if isinstance(result.get("data"), dict) else {}
    summary = str(data.get("summary") or "").strip()
    if not summary:
        raise AppError("The model did not return a research summary")
    signals = data.get("signals") or []
    if isinstance(signals, str):
        signals = [signals]
    return {
        "agent": "research",
        "title": "Company Research Agent",
        "summary": summary[:2000],
        "output": {"summary": summary[:2000], "signals": signals, "provider": result["provider"]},
        "note": result.get("note") or "",
    }


def enrich(db: Session, lead: Lead) -> dict:
    blob = " ".join([lead.notes or "", (lead.raw_payload or {}).get("snippet", ""), lead.source_url or ""])
    filled = []
    if not lead.email:
        found = extract_email(blob)
        if found:
            lead.email = found
            filled.append("email")
    if not lead.phone:
        found = extract_phone(blob)
        if found:
            lead.phone = found
            filled.append("phone")
    if not lead.website and lead.source_url:
        from app.search.normalize import company_website

        site = company_website(lead.source_url)
        if site:
            lead.website = site
            filled.append("website")
    return {
        "agent": "enrichment",
        "title": "Enrichment Agent",
        "summary": "Filled " + ", ".join(filled) if filled else "No new contact fields were found to fill.",
        "output": {
            "email": lead.email or "",
            "phone": lead.phone or "",
            "website": lead.website or "",
            "filled": filled,
        },
    }


def quality(db: Session, lead: Lead) -> dict:
    from app.search.normalize import dedup_key

    key = dedup_key(lead.company, lead.website or "")
    others = db.scalars(select(Lead.id).where(Lead.dedup_key == key, Lead.id != lead.id)).all()
    duplicate = bool(others)
    missing = [name for name, value in (("email", lead.email), ("phone", lead.phone), ("website", lead.website)) if not value]
    confidence = 85 - len(missing) * 15 - (25 if duplicate else 0)
    summary = "Possible duplicate of an existing lead." if duplicate else "No duplicate lead was found."
    if missing:
        summary += " Missing: " + ", ".join(missing) + "."
    return {
        "agent": "quality",
        "title": "Quality & Deduplication Agent",
        "summary": summary,
        "output": {"duplicate": duplicate, "duplicate_ids": list(others), "missing": missing, "confidence": max(confidence, 10)},
    }


def qualify(lead: Lead, llm, quality_step: dict, profile: dict | None = None) -> dict:
    result = llm.complete_json(
        purpose="lead_qualification",
        system=SYSTEM + " Do not mark the lead qualified. A person reviews that decision.",
        prompt=(
            "Score this lead from 0 to 100 for the business described below. "
            f"{profile_brief(profile)}\n"
            "JSON keys: score (integer), fit (low|medium|high), reasons (array of strings), recommend_qualify (boolean).\n"
            f"Company: {lead.company}\nContact: {lead.contact_name}\nEmail: {lead.email}\nPhone: {lead.phone}\n"
            f"Website: {lead.website}\nIndustry: {lead.industry}\nSize: {lead.company_size}\n"
            f"Region: {lead.city}, {lead.state}, {lead.country} {lead.postal_code}\n"
            f"Quality: {quality_step['output']}"
        ),
    )
    data = result["data"] if isinstance(result.get("data"), dict) else {}
    try:
        score = int(data["score"])
    except (KeyError, TypeError, ValueError):
        raise AppError("The model did not return a score") from None
    score = max(0, min(score, 100))
    reasons = data.get("reasons") or []
    if isinstance(reasons, str):
        reasons = [reasons]
    fit = str(data.get("fit") or "").strip().lower()
    if fit not in {"low", "medium", "high"}:
        fit = "high" if score >= 75 else "medium" if score >= 55 else "low"
    recommend = bool(data.get("recommend_qualify"))
    if quality_step["output"].get("duplicate"):
        recommend = False
    summary = f"Score {score}. " + "; ".join(str(item) for item in reasons[:3])
    return {
        "agent": "qualification",
        "title": "Lead Qualification Agent",
        "summary": summary[:500],
        "output": {
            "score": score,
            "fit": fit,
            "reasons": reasons,
            "recommend_qualify": recommend,
            "provider": result["provider"],
        },
        "note": result.get("note") or "",
    }


def outreach(lead: Lead, llm, qualification: dict, profile: dict | None = None) -> dict:
    contact = lead.contact_name or "there"
    result = llm.complete_json(
        purpose="outreach_draft",
        system=SYSTEM + " Write a short outreach email draft. Do not send it.",
        prompt=(
            "Write a concise outreach email draft for the seller below. JSON keys: subject, body. "
            "The body must say it is a draft and must not claim it was sent.\n"
            f"{profile_brief(profile)}\n"
            f"Company: {lead.company}\nContact: {contact}\nIndustry: {lead.industry}\n"
            f"Score: {qualification['output'].get('score')}\nReasons: {qualification['output'].get('reasons')}"
        ),
    )
    data = result["data"] if isinstance(result.get("data"), dict) else {}
    subject = str(data.get("subject") or "").strip()
    body = str(data.get("body") or "").strip()
    if not subject or not body:
        raise AppError("The model did not return an outreach draft")
    if "draft" not in body.lower():
        body += "\n\nThis is a draft. It has not been sent."
    return {
        "agent": "outreach",
        "title": "Outreach Drafting Agent",
        "summary": subject[:300],
        "output": {"subject": subject[:300], "body": body[:4000], "delivery": "draft", "provider": result["provider"]},
        "note": result.get("note") or "",
    }
