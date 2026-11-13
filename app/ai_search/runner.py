"""Run an AI search: plan, query, read, extract, then save scored leads."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai_search.extract import extract_companies, read_pages
from app.ai_search.planner import make_plan, refine_plan
from app.audit.service import record
from app.core.config import get_settings
from app.core.errors import AppError
from app.leads.service import ingest_lead
from app.models import AiSearchRun, Lead
from app.providers.access import consume
from app.search.providers import active_search_backends, search_query
from app.settings.profile import load_profile

THIN_RESULT_COUNT = 3


def run_ai_search(db: Session, actor, text: str, rounds: int | None = None) -> dict:
    request = (text or "").strip()
    if len(request) < 3:
        raise AppError("Describe who you want to find")
    limit = max(1, min(int(rounds or get_settings().ai_search_max_rounds or 2), 4))
    consume(db, actor, "ai_search", 1)
    profile = load_profile(db)
    plan = make_plan(db, actor, request, profile)
    collected = []
    sources = []
    providers = []
    used_rounds = 0
    for round_number in range(1, limit + 1):
        used_rounds = round_number
        found = _search_round(db, actor, plan, collected, sources, providers)
        if len({item["company"].lower() for item in collected}) >= THIN_RESULT_COUNT or round_number == limit:
            break
        plan = refine_plan(db, actor, request, plan, found)
    created, duplicates = _save(db, actor, collected)
    run = AiSearchRun(
        user_id=actor.id,
        text=request,
        plan=plan,
        rounds=used_rounds,
        created_count=created,
        duplicate_count=duplicates,
        providers=providers,
        sources=sources[:40],
    )
    db.add(run)
    record(
        db,
        user=actor,
        action="ai_search",
        module="search",
        target=request[:120],
        detail={"created": created, "duplicates": duplicates, "rounds": used_rounds, "queries": plan.get("queries")},
    )
    db.commit()
    db.refresh(run)
    return serialize_run(run)


def list_runs(db: Session) -> list[dict]:
    rows = db.scalars(select(AiSearchRun).order_by(AiSearchRun.id.desc()).limit(20)).all()
    return [serialize_run(row) for row in rows]


def source_counts(db: Session) -> dict:
    total = db.scalar(select(func.count()).select_from(Lead)) or 0
    grokbot = db.scalar(select(func.count()).select_from(Lead).where(Lead.source == "grokbot")) or 0
    return {"app": total - grokbot, "grokbot": grokbot, "total": total}


def serialize_run(run: AiSearchRun) -> dict:
    return {
        "id": run.id,
        "text": run.text,
        "plan": run.plan or {},
        "rounds": run.rounds,
        "created_count": run.created_count,
        "duplicate_count": run.duplicate_count,
        "providers": run.providers or [],
        "sources": run.sources or [],
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


def _search_round(db, actor, plan, collected, sources, providers) -> int:
    before = len(collected)
    seen = {item["company"].lower() for item in collected}
    for query in plan.get("queries") or []:
        hits = search_query(db, query, limit=4)
        for hit in hits:
            provider = hit.get("search_provider") or ""
            if provider not in providers:
                providers.append(provider)
            if hit.get("source_url"):
                sources.append({"query": query, "provider": provider, "url": hit.get("source_url"), "title": hit.get("company") or ""})
        pages = read_pages(hits, limit=3)
        for company in extract_companies(db, actor, pages, plan):
            name = company["company"].strip().lower()
            if name in seen:
                continue
            seen.add(name)
            collected.append(company)
    if not providers:
        providers.extend(active_search_backends(db))
    return len(collected) - before


def _save(db, actor, companies) -> tuple[int, int]:
    created = 0
    duplicates = 0
    for company in companies:
        outcome = ingest_lead(db, actor, company, source="ai-search")
        if outcome == "created":
            created += 1
        elif outcome == "duplicate":
            duplicates += 1
    return created, duplicates
