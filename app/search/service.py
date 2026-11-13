"""Save target profiles, run a search, and store deduplicated leads."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.errors import AppError
from app.models import Lead, SearchCriteria, SearchRun, User
from app.providers.access import consume
from app.search.normalize import dedup_key
from app.search.presets import clean_criteria
from app.search.providers import search_companies


def criteria_dict(row: SearchCriteria) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "industry": row.industry or "",
        "keywords": row.keywords or "",
        "company_size": row.company_size or "",
        "country": row.country or "",
        "state": row.state or "",
        "district": row.district or "",
        "city": row.city or "",
        "postal_code": row.postal_code or "",
        "radius_km": row.radius_km,
        "results_limit": row.results_limit,
        "states": list(row.states or []),
        "opportunity_type": row.opportunity_type or "",
        "buyer_type": row.buyer_type or "",
        "role_category": row.role_category or "",
        "posted_window": row.posted_window or "",
        "min_score": row.min_score,
        "query_templates": list(row.query_templates or []),
        "owner_id": row.owner_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_criteria(db: Session) -> list[dict]:
    rows = db.scalars(select(SearchCriteria).order_by(SearchCriteria.id.desc())).all()
    return [criteria_dict(row) for row in rows]


def save_criteria(db: Session, actor: User, payload: dict) -> dict:
    name = (payload.get("name") or "").strip()
    if len(name) < 2:
        raise AppError("Give this search a name")
    cleaned = clean_criteria(payload)
    single_state = cleaned["states"][0] if len(cleaned["states"]) == 1 else (payload.get("state") or "").strip()
    if len(cleaned["states"]) != 1:
        single_state = ""
    row = SearchCriteria(
        name=name[:160],
        owner_id=actor.id,
        industry=cleaned["industry"],
        keywords=cleaned["keywords"],
        company_size=cleaned["company_size"],
        country=cleaned["country"],
        state=single_state[:80],
        states=cleaned["states"],
        district=cleaned["district"],
        city=cleaned["city"],
        postal_code=cleaned["postal_code"],
        opportunity_type=cleaned["opportunity_type"],
        buyer_type=cleaned["buyer_type"],
        role_category=cleaned["role_category"],
        posted_window=cleaned["posted_window"],
        min_score=cleaned["min_score"],
        query_templates=cleaned["query_templates"],
        radius_km=payload.get("radius_km"),
        results_limit=_limit(payload.get("results_limit")),
    )
    db.add(row)
    db.flush()
    record(db, user=actor, action="search_criteria_saved", module="search", target=str(row.id), detail={"name": row.name})
    db.commit()
    db.refresh(row)
    return criteria_dict(row)


def delete_criteria(db: Session, actor: User, criteria_id: int) -> None:
    row = db.get(SearchCriteria, criteria_id)
    if row is None:
        raise AppError("Search criteria not found", 404)
    db.delete(row)
    record(db, user=actor, action="search_criteria_deleted", module="search", target=str(criteria_id))
    db.commit()


def run_saved_search(db: Session, actor: User, criteria_id: int) -> dict:
    criteria = db.get(SearchCriteria, criteria_id)
    if criteria is None:
        raise AppError("Search criteria not found", 404)
    from app.search.providers import choose_search_provider

    choose_search_provider(db)
    consume(db, actor, "search", 1)
    provider, query, rows = search_companies(db, criteria)
    created = 0
    duplicates = 0
    lead_ids = []
    for item in rows:
        company = (item.get("company") or "").strip()
        if len(company) < 2:
            continue
        website = (item.get("website") or "").strip()
        key = dedup_key(company, website)
        if db.scalar(select(Lead.id).where(Lead.dedup_key == key)):
            duplicates += 1
            continue
        lead = Lead(
            company=company,
            contact_name=(item.get("contact_name") or "").strip(),
            email=(item.get("email") or "").strip(),
            phone=(item.get("phone") or "").strip(),
            website=website,
            source=item.get("source") or provider,
            source_url=(item.get("source_url") or website or "").strip(),
            country=(item.get("country") or criteria.country or "").strip(),
            state=(item.get("state") or criteria.state or "").strip(),
            district=(item.get("district") or criteria.district or "").strip(),
            city=(item.get("city") or criteria.city or "").strip(),
            postal_code=(item.get("postal_code") or criteria.postal_code or "").strip(),
            industry=(item.get("industry") or criteria.industry or "").strip(),
            company_size=(item.get("company_size") or criteria.company_size or "").strip(),
            keywords=(item.get("keywords") or criteria.keywords or "").strip(),
            status="New",
            estimated_value=int(item.get("estimated_value") or 0),
            notes=(item.get("snippet") or "").strip(),
            owner_id=actor.id,
            created_by=actor.id,
            dedup_key=key,
            raw_payload={"snippet": item.get("snippet") or "", "query": query, "provider": provider},
        )
        try:
            with db.begin_nested():
                db.add(lead)
                db.flush()
        except IntegrityError:
            duplicates += 1
            continue
        created += 1
        lead_ids.append(lead.id)
    run = SearchRun(
        criteria_id=criteria.id,
        user_id=actor.id,
        provider=provider,
        query=query,
        status="completed",
        fetched=len(rows),
        created_count=created,
        duplicate_count=duplicates,
    )
    db.add(run)
    record(
        db,
        user=actor,
        action="search",
        module="search",
        target=str(criteria.id),
        detail={"provider": provider, "created": created, "duplicates": duplicates, "query": query},
    )
    db.commit()
    db.refresh(run)
    return run_dict(run) | {"lead_ids": lead_ids}


def list_runs(db: Session) -> list[dict]:
    rows = db.scalars(select(SearchRun).order_by(SearchRun.id.desc()).limit(50)).all()
    return [run_dict(row) for row in rows]


def run_dict(row: SearchRun) -> dict:
    return {
        "id": row.id,
        "criteria_id": row.criteria_id,
        "provider": row.provider,
        "query": row.query,
        "status": row.status,
        "fetched": row.fetched,
        "created_count": row.created_count,
        "duplicate_count": row.duplicate_count,
        "error": row.error or "",
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _limit(value) -> int:
    try:
        number = int(value or 10)
    except (TypeError, ValueError):
        number = 10
    return max(1, min(number, 1000))
