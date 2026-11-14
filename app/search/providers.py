"""Web search providers. Tavily and Brave run only when a key is configured."""

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.providers.secrets import resolve_secret
from app.search.normalize import clean_title, company_website, extract_email, extract_phone

SEARCH_PROVIDERS = ("tavily", "brave")
NO_SEARCH_PROVIDER = "No search provider configured"


def choose_search_provider(db) -> tuple[str, str | None]:
    settings = get_settings()
    requested = (settings.search_provider or "auto").strip().lower()
    if requested in {"tavily", "brave"}:
        key = _key_for(db, settings, requested)
        if not key:
            raise AppError(NO_SEARCH_PROVIDER, 400)
        return requested, key
    for name in SEARCH_PROVIDERS:
        key = _key_for(db, settings, name)
        if key:
            return name, key
    raise AppError(NO_SEARCH_PROVIDER, 400)


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
    rows = _search_backend(provider, key or "", query, limit)
    return provider, query, rows


def build_query(criteria) -> str:
    from app.search.presets import compose_query

    return compose_query(criteria)


def _search_backend(provider: str, key: str, query: str, limit: int) -> list[dict]:
    if provider == "tavily":
        return tavily_search(key, query, limit)
    if provider == "brave":
        return brave_search(key, query, limit)
    raise AppError(NO_SEARCH_PROVIDER, 400)


def tavily_search(api_key: str, query: str, limit: int) -> list[dict]:
    return parse_tavily_results(_tavily_payload(api_key, query, limit))


def _tavily_payload(api_key: str, query: str, limit: int) -> dict:
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                "https://api.tavily.com/search",
                json={"api_key": api_key, "query": query, "max_results": limit, "include_answer": False},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise AppError(f"Tavily search failed: {exc.__class__.__name__}", 502) from exc


def parse_tavily_results(payload: dict) -> list[dict]:
    rows = []
    for item in payload.get("results") or []:
        rows.append(_from_web_result(item.get("title", ""), item.get("url", ""), item.get("content", ""), "tavily"))
    return [row for row in rows if row["company"]]


def brave_search(api_key: str, query: str, limit: int) -> list[dict]:
    return parse_brave_results(_brave_payload(api_key, query, limit))


def _brave_payload(api_key: str, query: str, limit: int) -> dict:
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": limit},
                headers={"Accept": "application/json", "X-Subscription-Token": api_key},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise AppError(f"Brave search failed: {exc.__class__.__name__}", 502) from exc


def search_documents(db, query: str, limit: int = 10) -> tuple[str, list[dict]]:
    """Public pages as title, url, and snippet. A company name is not required."""
    provider, key = choose_search_provider(db)
    bounded = max(1, min(int(limit or 10), 10))
    if provider == "tavily":
        payload = _tavily_payload(key or "", query, bounded)
        raw_rows = payload.get("results") or []
        rows = [
            {"title": item.get("title") or "", "url": item.get("url") or "", "snippet": item.get("content") or ""}
            for item in raw_rows
            if isinstance(item, dict)
        ]
    elif provider == "brave":
        payload = _brave_payload(key or "", query, bounded)
        raw_rows = (payload.get("web") or {}).get("results") or []
        rows = [
            {"title": item.get("title") or "", "url": item.get("url") or "", "snippet": item.get("description") or ""}
            for item in raw_rows
            if isinstance(item, dict)
        ]
    else:
        raise AppError(NO_SEARCH_PROVIDER, 400)
    return provider, [row for row in rows if row["url"]]


def parse_brave_results(payload: dict) -> list[dict]:
    web = (payload.get("web") or {}).get("results") or []
    rows = []
    for item in web:
        rows.append(_from_web_result(item.get("title", ""), item.get("url", ""), item.get("description", ""), "brave"))
    return [row for row in rows if row["company"]]


def active_search_backends(db) -> list[str]:
    """Configured Tavily and Brave backends. Never includes a fabricated source."""
    settings = get_settings()
    requested = (settings.search_provider or "auto").strip().lower()
    if requested in SEARCH_PROVIDERS:
        return [requested] if _key_for(db, settings, requested) else []
    return [name for name in SEARCH_PROVIDERS if _key_for(db, settings, name)]


def search_query(db, query: str, limit: int = 5) -> list[dict]:
    settings = get_settings()
    backends = active_search_backends(db)
    if not backends:
        raise AppError(NO_SEARCH_PROVIDER, 400)
    hits = []
    bounded = max(1, min(int(limit or 5), 8))
    for name in backends:
        rows = _search_backend(name, _key_for(db, settings, name) or "", query, bounded)
        for row in rows:
            row["search_provider"] = name
            row["query"] = query
            hits.append(row)
    return hits


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
