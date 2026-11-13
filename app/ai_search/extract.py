"""Read search hits and pull out company and contact fields."""

import re

import httpx

from app.providers.llm import LLMClient
from app.search.normalize import clean_title, company_website, extract_email, extract_phone

EXTRACT_SYSTEM = (
    "Extract companies from page text. Return only JSON: "
    "{\"companies\": [{\"company\", \"contact_name\", \"email\", \"phone\", \"website\", "
    "\"city\", \"state\", \"country\", \"industry\", \"why_fit\", \"source_url\"}]}. "
    "Leave unknown fields as empty strings. Do not invent email addresses."
)


def read_pages(hits: list[dict], limit: int = 3) -> list[dict]:
    pages = []
    for hit in hits:
        if len(pages) >= limit:
            break
        url = hit.get("source_url") or hit.get("website") or ""
        text = hit.get("snippet") or ""
        if _should_fetch(url):
            fetched = fetch_text(url)
            if fetched:
                text = fetched
        pages.append({**hit, "text": (text or "")[:5000], "source_url": url})
    return pages


def fetch_text(url: str) -> str:
    try:
        with httpx.Client(timeout=8, follow_redirects=True) as client:
            response = client.get(url, headers={"User-Agent": "LeadPilotAI/1.0"})
            response.raise_for_status()
    except httpx.HTTPError:
        return ""
    content_type = response.headers.get("content-type", "")
    if "html" not in content_type and "text" not in content_type and content_type:
        return ""
    text = re.sub(r"(?is)<script.*?>.*?</script>|<style.*?>.*?</style>", " ", response.text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:5000]


def companies_from_pages(pages: list[dict], plan: dict) -> list[dict]:
    rows = []
    seen = set()
    for page in pages:
        company = (page.get("company") or clean_title(page.get("title") or "")).strip()
        if len(company) < 2 or company.lower() in seen:
            continue
        seen.add(company.lower())
        blob = page.get("text") or page.get("snippet") or ""
        rows.append(
            {
                "company": company,
                "contact_name": page.get("contact_name") or "",
                "email": page.get("email") or extract_email(blob),
                "phone": page.get("phone") or extract_phone(blob),
                "website": page.get("website") or company_website(page.get("source_url") or ""),
                "city": page.get("city") or "",
                "state": page.get("state") or "",
                "country": page.get("country") or "",
                "district": page.get("district") or "",
                "postal_code": page.get("postal_code") or "",
                "industry": page.get("industry") or (plan.get("profile") or "")[:120],
                "why_fit": page.get("why_fit") or f"Matches the request: {plan.get('profile', '')}"[:500],
                "source_url": page.get("source_url") or "",
                "snippet": (page.get("snippet") or blob)[:500],
                "keywords": ", ".join(plan.get("signals") or [])[:500],
                "estimated_value": page.get("estimated_value") or 0,
            }
        )
    return rows


def extract_companies(db, user, pages: list[dict], plan: dict) -> list[dict]:
    fallback_rows = companies_from_pages(pages, plan)
    if not pages:
        return []
    packed = []
    for page in pages[:4]:
        packed.append(
            {
                "title": page.get("company") or page.get("title") or "",
                "url": page.get("source_url") or "",
                "text": (page.get("text") or "")[:1500],
            }
        )
    result = LLMClient(db, user).complete_json(
        purpose="ai_search_extract",
        system=EXTRACT_SYSTEM,
        prompt=(
            f"Target profile: {plan.get('profile')}\n"
            f"Locations: {plan.get('locations')}\nSignals: {plan.get('signals')}\n"
            f"Pages: {packed}"
        ),
        fallback={"companies": fallback_rows},
    )
    raw_rows = result["data"].get("companies") if isinstance(result["data"], dict) else None
    if not isinstance(raw_rows, list) or not raw_rows:
        return fallback_rows
    cleaned = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        company = str(row.get("company") or "").strip()
        if len(company) < 2:
            continue
        cleaned.append(
            {
                "company": company,
                "contact_name": str(row.get("contact_name") or ""),
                "email": str(row.get("email") or ""),
                "phone": str(row.get("phone") or ""),
                "website": str(row.get("website") or ""),
                "city": str(row.get("city") or ""),
                "state": str(row.get("state") or ""),
                "country": str(row.get("country") or ""),
                "industry": str(row.get("industry") or ""),
                "why_fit": str(row.get("why_fit") or "")[:500],
                "source_url": str(row.get("source_url") or ""),
                "snippet": str(row.get("why_fit") or "")[:500],
            }
        )
    return cleaned or fallback_rows


def _should_fetch(url: str) -> bool:
    if not url.startswith("http"):
        return False
    host = url.split("/")[2].lower()
    return not host.endswith(".example") and "example.com" not in host
