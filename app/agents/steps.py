"""Specialist agents. Outreach produces a draft and never sends mail."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lead
from app.search.normalize import extract_email, extract_phone

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


def research(lead: Lead, llm) -> dict:
    snippet = (lead.raw_payload or {}).get("snippet") or lead.notes or ""
    fallback = {
        "summary": snippet or f"{lead.company} is a {lead.industry or 'business'} organization in {lead.city or lead.country or 'the target region'}.",
        "signals": [part for part in [lead.industry, lead.company_size, lead.keywords] if part],
    }
    result = llm.complete_json(
        purpose="company_research",
        system=SYSTEM,
        prompt=(
            "Summarize this company for a recruiter. JSON keys: summary (string), signals (array of short strings).\n"
            f"Company: {lead.company}\nIndustry: {lead.industry}\nLocation: {lead.city}, {lead.state}, {lead.country}\n"
            f"Website: {lead.website}\nNotes: {snippet}"
        ),
        fallback=fallback,
    )
    data = result["data"]
    summary = str(data.get("summary") or fallback["summary"])[:2000]
    return {
        "agent": "research",
        "title": "Company Research Agent",
        "summary": summary,
        "output": {"summary": summary, "signals": data.get("signals") or fallback["signals"], "provider": result["provider"]},
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


def qualify(lead: Lead, llm, quality_step: dict) -> dict:
    base = _heuristic_score(lead, quality_step["output"])
    fallback = {
        "score": base,
        "fit": "high" if base >= 75 else "medium" if base >= 55 else "low",
        "reasons": _reasons(lead, quality_step["output"]),
        "recommend_qualify": base >= 65 and not quality_step["output"].get("duplicate"),
    }
    result = llm.complete_json(
        purpose="lead_qualification",
        system=SYSTEM + " Do not mark the lead qualified. A person reviews that decision.",
        prompt=(
            "Score this lead from 0 to 100 for a recruitment sales team. "
            "JSON keys: score (integer), fit (low|medium|high), reasons (array of strings), recommend_qualify (boolean).\n"
            f"Company: {lead.company}\nContact: {lead.contact_name}\nEmail: {lead.email}\nPhone: {lead.phone}\n"
            f"Website: {lead.website}\nIndustry: {lead.industry}\nSize: {lead.company_size}\n"
            f"Region: {lead.city}, {lead.state}, {lead.country} {lead.postal_code}\n"
            f"Quality: {quality_step['output']}"
        ),
        fallback=fallback,
    )
    data = result["data"]
    try:
        score = int(data.get("score", fallback["score"]))
    except (TypeError, ValueError):
        score = fallback["score"]
    score = max(0, min(score, 100))
    reasons = data.get("reasons") or fallback["reasons"]
    if isinstance(reasons, str):
        reasons = [reasons]
    recommend = bool(data.get("recommend_qualify", fallback["recommend_qualify"]))
    if quality_step["output"].get("duplicate"):
        recommend = False
    summary = f"Score {score}. " + "; ".join(str(item) for item in reasons[:3])
    return {
        "agent": "qualification",
        "title": "Lead Qualification Agent",
        "summary": summary[:500],
        "output": {
            "score": score,
            "fit": data.get("fit") or fallback["fit"],
            "reasons": reasons,
            "recommend_qualify": recommend,
            "provider": result["provider"],
        },
        "note": result.get("note") or "",
    }


def outreach(lead: Lead, llm, qualification: dict) -> dict:
    contact = lead.contact_name or "there"
    fallback = {
        "subject": f"Idea for {lead.company}'s hiring plans",
        "body": (
            f"Hello {contact},\n\n"
            f"I came across {lead.company} while looking at {lead.industry or 'growing'} teams"
            f"{' in ' + lead.city if lead.city else ''}. "
            "We help companies staff critical roles without a long search cycle.\n\n"
            "Would you be open to a short conversation next week?\n\n"
            "— LinkTMS / CanberraAI LeadPilot\n\n"
            "This is a draft. It has not been sent."
        ),
    }
    result = llm.complete_json(
        purpose="outreach_draft",
        system=SYSTEM + " Write a short outreach email draft. Do not send it.",
        prompt=(
            "Write a concise outreach email draft. JSON keys: subject, body. "
            "The body must say it is a draft and must not claim it was sent.\n"
            f"Company: {lead.company}\nContact: {contact}\nIndustry: {lead.industry}\n"
            f"Score: {qualification['output'].get('score')}\nReasons: {qualification['output'].get('reasons')}"
        ),
        fallback=fallback,
    )
    data = result["data"]
    subject = str(data.get("subject") or fallback["subject"])[:300]
    body = str(data.get("body") or fallback["body"])[:4000]
    if "draft" not in body.lower():
        body += "\n\nThis is a draft. It has not been sent."
    return {
        "agent": "outreach",
        "title": "Outreach Drafting Agent",
        "summary": subject,
        "output": {"subject": subject, "body": body, "delivery": "draft", "provider": result["provider"]},
        "note": result.get("note") or "",
    }


def _heuristic_score(lead: Lead, quality: dict) -> int:
    score = 35
    if lead.email:
        score += 15
    if lead.phone:
        score += 10
    if lead.website:
        score += 10
    if lead.industry:
        score += 10
    if lead.city or lead.country:
        score += 8
    if lead.contact_name:
        score += 7
    score += int(quality.get("confidence", 50) / 10)
    if quality.get("duplicate"):
        score -= 30
    return max(0, min(score, 96))


def _reasons(lead: Lead, quality: dict) -> list[str]:
    reasons = []
    if lead.industry:
        reasons.append(f"Industry match: {lead.industry}")
    if lead.email:
        reasons.append("A contact email is on file")
    else:
        reasons.append("No contact email yet")
    if quality.get("duplicate"):
        reasons.append("Possible duplicate")
    if lead.city or lead.country:
        reasons.append(f"Located in {', '.join(part for part in (lead.city, lead.country) if part)}")
    return reasons or ["Limited public information"]
