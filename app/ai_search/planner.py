"""Turn a free-text request into a small search plan."""

import re

from app.core.errors import AppError
from app.providers.llm import LLMClient
from app.search.presets import criteria_brief
from app.settings.profile import profile_brief

PLAN_SYSTEM = (
    "You plan web searches that find companies to sell to. "
    "Return only JSON with keys profile (string), locations (array of strings), "
    "signals (array of strings), and queries (array of 3 to 8 search queries). "
    "Queries must be concrete enough to paste into a web search engine."
)


def normalize_plan(raw: dict | None, text: str) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    profile = str(raw.get("profile") or "").strip()[:300]
    if not profile:
        profile = re.sub(r"\s+", " ", (text or "").strip())[:300]
    queries = [item[:180] for item in _string_list(raw.get("queries"))][:8]
    if not profile or not queries:
        raise AppError("The model did not return a search plan")
    return {
        "profile": profile,
        "locations": _string_list(raw.get("locations"))[:6],
        "signals": _string_list(raw.get("signals"))[:8],
        "queries": queries,
    }


def make_plan(db, user, text: str, profile: dict, criteria: dict | None = None) -> dict:
    brief = criteria_brief(criteria)
    result = LLMClient(db, user).complete_json(
        purpose="ai_search_plan",
        system=PLAN_SYSTEM,
        prompt=(
            f"{profile_brief(profile)}\n"
            "Turn this request into a search plan. Use the query templates when they fit the request.\n"
            f"{brief}\n"
            f"Request: {text.strip()}"
        ),
    )
    plan = normalize_plan(result["data"], text)
    plan["provider"] = result["provider"]
    plan["note"] = result.get("note") or ""
    return plan


def refine_plan(db, user, text: str, plan: dict, found: int) -> dict:
    result = LLMClient(db, user).complete_json(
        purpose="ai_search_refine",
        system=PLAN_SYSTEM,
        prompt=(
            f"The last round found only {found} companies for: {text.strip()}\n"
            f"Previous queries: {plan.get('queries')}\n"
            "Return JSON with a queries array of 3 to 8 better searches."
        ),
    )
    data = result["data"] if isinstance(result.get("data"), dict) else {}
    queries = [item[:180] for item in _string_list(data.get("queries"))][:8]
    if not queries:
        raise AppError("The model did not return search queries")
    updated = dict(plan)
    updated["queries"] = queries
    updated["provider"] = result["provider"]
    return updated


def _string_list(value) -> list[str]:
    if isinstance(value, str):
        value = re.split(r"[\n,;]", value)
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        text = str(item or "").strip()
        if len(text) > 2 and text not in items:
            items.append(text)
    return items
