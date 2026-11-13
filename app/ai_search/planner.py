"""Turn a free-text request into a small search plan."""

import re

from app.providers.llm import LLMClient
from app.settings.profile import profile_brief

PLAN_SYSTEM = (
    "You plan web searches that find companies to sell to. "
    "Return only JSON with keys profile (string), locations (array of strings), "
    "signals (array of strings), and queries (array of 3 to 8 search queries). "
    "Queries must be concrete enough to paste into a web search engine."
)


def fallback_plan(text: str) -> dict:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if len(cleaned) < 3:
        cleaned = "companies to contact"
    locations = _locations(cleaned)
    signals = _signals(cleaned)
    queries = []
    for suffix in ("", " companies", " contact email", " suppliers", " directory"):
        query = (cleaned + suffix).strip()
        if query not in queries:
            queries.append(query[:180])
        if len(queries) >= 4:
            break
    return {"profile": cleaned[:300], "locations": locations, "signals": signals, "queries": queries}


def normalize_plan(raw: dict | None, text: str) -> dict:
    fallback = fallback_plan(text)
    raw = raw if isinstance(raw, dict) else {}
    profile = str(raw.get("profile") or fallback["profile"]).strip()[:300] or fallback["profile"]
    locations = _string_list(raw.get("locations"))[:6] or fallback["locations"]
    signals = _string_list(raw.get("signals"))[:8] or fallback["signals"]
    queries = [item[:180] for item in _string_list(raw.get("queries"))]
    for item in fallback["queries"]:
        if len(queries) >= 3:
            break
        if item not in queries:
            queries.append(item)
    if not queries:
        queries = fallback["queries"]
    return {"profile": profile, "locations": locations, "signals": signals, "queries": queries[:8]}


def make_plan(db, user, text: str, profile: dict) -> dict:
    fallback = fallback_plan(text)
    result = LLMClient(db, user).complete_json(
        purpose="ai_search_plan",
        system=PLAN_SYSTEM,
        prompt=(
            f"{profile_brief(profile)}\n"
            "Turn this request into a search plan.\n"
            f"Request: {text.strip()}"
        ),
        fallback=fallback,
    )
    plan = normalize_plan(result["data"], text)
    plan["provider"] = result["provider"]
    plan["note"] = result.get("note") or ""
    return plan


def refine_plan(db, user, text: str, plan: dict, found: int) -> dict:
    extra = []
    for query in plan.get("queries") or []:
        broadened = f"{query} official site"
        if broadened not in extra:
            extra.append(broadened[:180])
    fallback = {"queries": (list(plan.get("queries") or []) + extra)[:8]}
    result = LLMClient(db, user).complete_json(
        purpose="ai_search_refine",
        system=PLAN_SYSTEM,
        prompt=(
            f"The last round found only {found} companies for: {text.strip()}\n"
            f"Previous queries: {plan.get('queries')}\n"
            "Return JSON with a queries array of 3 to 8 better searches."
        ),
        fallback=fallback,
    )
    updated = dict(plan)
    updated["queries"] = normalize_plan({"queries": result["data"].get("queries"), "profile": plan.get("profile")}, text)["queries"]
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


def _locations(text: str) -> list[str]:
    known = ["Gujarat", "India", "Maharashtra", "Karnataka", "Vadodara", "Ahmedabad", "Mumbai", "United States", "California"]
    found = [name for name in known if name.lower() in text.lower()]
    return found[:6]


def _signals(text: str) -> list[str]:
    pieces = re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}", text or "")
    skip = {"that", "with", "from", "this", "have", "might", "buy", "uses", "using", "and", "for", "the"}
    signals = []
    for piece in pieces:
        if piece.lower() in skip:
            continue
        if piece not in signals:
            signals.append(piece)
        if len(signals) >= 6:
            break
    return signals
