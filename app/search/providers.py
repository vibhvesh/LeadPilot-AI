"""Web search providers. Mock is the default; Tavily and Brave are used when a key exists."""

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.providers.secrets import resolve_secret
from app.search.catalog import CATALOG, synthesize
from app.search.normalize import clean_title, company_website, extract_email, extract_phone, split_keywords

SEARCH_PROVIDERS = ("mock", "tavily", "brave")


def choose_search_provider(db) -> tuple[str, str | None]:
    settings = get_settings()
    requested = (settings.search_provider or "auto").strip().lower()
    if requested == "mock":
        return "mock", None
    if requested in {"tavily", "brave"}:
        key = _key_for(db, settings, requested)
        if not key:
            raise AppError(f"The {requested} search provider is selected but no API key is configured", 400)
        return requested, key
    for name in ("tavily", "brave"):
        key = _key_for(db, settings, name)
        if key:
            return name, key
    return "mock", None


def _key_for(db, settings: Settings, provider: str) -> str | None:
    if provider == "tavily":
        env_value = settings.tavily_api_key or (settings.search_api_key if settings.search_provider in {"auto", "tavily"} else "")
    elif provider == "brave":
        env_value = settings.brave_api_key or (settings.search_api_key if settings.search_provider == "brave" else "")
    else:
        env_value = ""
    return resolve_secret(db, provider, env_value)


def search_companies(db, criteria) -> tuple[str, str, list[dict]]:
    provider, key = choose_search_provider(db)
    query = build_query(criteria)
    limit = max(1, min(int(criteria.results_limit or 10), 25))
    if provider == "tavily":
        rows = tavily_search(key, query, limit)
    elif provider == "brave":
        rows = brave_search(key, query, limit)
    else:
        rows = mock_search(criteria, limit)
    return provider, query, rows


def build_query(criteria) -> str:
    parts = []
    if criteria.keywords:
        parts.append(criteria.keywords)
    if criteria.industry:
        parts.append(criteria.industry)
    parts.append("companies")
    location = ", ".join(
        piece
        for piece in (criteria.city, criteria.district, criteria.state, criteria.country, criteria.postal_code)
        if piece
    )
    if location:
        parts.append("in " + location)
    if criteria.company_size and criteria.company_size != "Any size":
        parts.append(criteria.company_size + " employees")
    return " ".join(parts)


def mock_search(criteria, limit: int) -> list[dict]:
    scored = []
    for item in CATALOG:
        score = _catalog_score(item, criteria)
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    chosen = [dict(item) for _score, item in scored[:limit]]
    if not chosen:
        chosen = synthesize(criteria, count=min(5, limit))
    for item in chosen:
        item["source"] = "mock-search"
        item.setdefault("estimated_value", 180000)
    return chosen


def _catalog_score(item: dict, criteria) -> int:
    blob = " ".join(
        [
            item.get("industry", ""),
            item.get("keywords", ""),
            item.get("company", ""),
            item.get("snippet", ""),
        ]
    ).lower()
    score = 0
    if criteria.industry:
        if criteria.industry.lower() not in blob:
            return 0
        score += 3
    if criteria.keywords:
        hits = [word for word in split_keywords(criteria.keywords) if word.lower() in blob]
        if not hits:
            return 0
        score += len(hits)
    for field in ("country", "state", "district", "city"):
        wanted = getattr(criteria, field, "") or ""
        if wanted and wanted.lower() not in (item.get(field, "") or "").lower():
            return 0
        if wanted:
            score += 1
    if criteria.postal_code and criteria.postal_code not in (item.get("postal_code") or ""):
        return 0
    size = criteria.company_size or ""
    if size and size != "Any size" and size != item.get("company_size"):
        return 0
    if score == 0:
        return 1
    return score


def tavily_search(api_key: str, query: str, limit: int) -> list[dict]:
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                "https://api.tavily.com/search",
                json={"api_key": api_key, "query": query, "max_results": limit, "include_answer": False},
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise AppError(f"Tavily search failed: {exc.__class__.__name__}", 502) from exc
    return parse_tavily_results(payload)


def parse_tavily_results(payload: dict) -> list[dict]:
    rows = []
    for item in payload.get("results") or []:
        rows.append(_from_web_result(item.get("title", ""), item.get("url", ""), item.get("content", ""), "tavily"))
    return [row for row in rows if row["company"]]


def brave_search(api_key: str, query: str, limit: int) -> list[dict]:
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": limit},
                headers={"Accept": "application/json", "X-Subscription-Token": api_key},
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise AppError(f"Brave search failed: {exc.__class__.__name__}", 502) from exc
    return parse_brave_results(payload)


def parse_brave_results(payload: dict) -> list[dict]:
    web = (payload.get("web") or {}).get("results") or []
    rows = []
    for item in web:
        rows.append(_from_web_result(item.get("title", ""), item.get("url", ""), item.get("description", ""), "brave"))
    return [row for row in rows if row["company"]]


def _from_web_result(title: str, url: str, text: str, source: str) -> dict:
    combined = f"{title}\n{text}"
    return {
        "company": clean_title(title),
        "contact_name": "",
        "email": extract_email(combined),
        "phone": extract_phone(combined),
        "website": company_website(url),
        "source": source,
        "source_url": url or "",
        "snippet": (text or "")[:1000],
        "industry": "",
        "keywords": "",
        "company_size": "",
        "country": "",
        "state": "",
        "district": "",
        "city": "",
        "postal_code": "",
        "estimated_value": 0,
    }
