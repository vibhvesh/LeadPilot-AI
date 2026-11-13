"""Workspace preferences and the default geographic target."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_module
from app.models import WorkspaceSettings

router = APIRouter(prefix="/api")


def _apply_icp(row: WorkspaceSettings, body: dict) -> None:
    from app.search.presets import clean_criteria

    if not any(key in body for key in ("icp_country", "icp_states", "icp_keywords", "icp_opportunity_type")):
        return
    payload = {
        "country": body.get("icp_country", row.icp_country),
        "states": body.get("icp_states", row.icp_states or []),
        "city": body.get("icp_city", row.icp_city),
        "opportunity_type": body.get("icp_opportunity_type", row.icp_opportunity_type),
        "buyer_type": body.get("icp_buyer_type", row.icp_buyer_type),
        "role_category": body.get("icp_role_category", row.icp_role_category),
        "industry": body.get("icp_industry", row.icp_industry),
        "company_size": body.get("icp_company_size", row.icp_company_size),
        "posted_window": body.get("icp_posted_window", row.icp_posted_window),
        "min_score": body.get("icp_min_score", row.icp_min_score),
        "keywords": body.get("icp_keywords", row.icp_keywords),
    }
    cleaned = clean_criteria(payload, default_country="United States")
    row.icp_country = cleaned["country"] or "United States"
    row.icp_states = cleaned["states"]
    row.icp_city = cleaned["city"]
    row.icp_opportunity_type = cleaned["opportunity_type"]
    row.icp_buyer_type = cleaned["buyer_type"]
    row.icp_role_category = cleaned["role_category"]
    row.icp_industry = cleaned["industry"]
    row.icp_company_size = cleaned["company_size"]
    row.icp_posted_window = cleaned["posted_window"]
    row.icp_min_score = cleaned["min_score"]
    row.icp_keywords = cleaned["keywords"]


def _settings(db: Session) -> WorkspaceSettings:
    row = db.get(WorkspaceSettings, 1)
    if row is None:
        row = WorkspaceSettings(id=1)
        db.add(row)
        db.flush()
    return row


def _public(row: WorkspaceSettings) -> dict:
    settings = get_settings()
    database = "postgresql" if settings.resolved_database_url().startswith("postgresql") else "sqlite"
    return {
        "workspace_name": row.workspace_name,
        "product_name": row.product_name,
        "seller_name": row.seller_name or "LinkTMS",
        "offering": row.offering or "We help companies staff critical roles without a long search cycle.",
        "ideal_customer": row.ideal_customer or "US companies hiring for US-based roles that want to hire, or are open to, recruitment vendors and staffing agencies.",
        "currency": row.currency,
        "retention_days": row.retention_days,
        "country": row.country or "",
        "state": row.state or "",
        "district": row.district or "",
        "city": row.city or "",
        "postal_code": row.postal_code or "",
        "radius_km": row.radius_km,
        "icp_country": row.icp_country or "United States",
        "icp_states": list(row.icp_states or []),
        "icp_city": row.icp_city or "",
        "icp_opportunity_type": row.icp_opportunity_type or "",
        "icp_buyer_type": row.icp_buyer_type or "",
        "icp_role_category": row.icp_role_category or "",
        "icp_industry": row.icp_industry or "",
        "icp_company_size": row.icp_company_size or "",
        "icp_posted_window": row.icp_posted_window or "",
        "icp_min_score": row.icp_min_score,
        "icp_keywords": row.icp_keywords or "",
        "authentication": "Google sign-in" + (" and demo sign-in" if settings.demo_mode else ""),
        "demo_mode": settings.demo_mode,
        "database": database,
        "super_admin": settings.super_admin,
    }


@router.get("/settings")
def get_workspace(db: Session = Depends(get_db), _user=Depends(require_module("settings"))):
    return _public(_settings(db))


@router.put("/settings")
def put_workspace(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("settings", manage=True))):
    row = _settings(db)
    if body.get("workspace_name"):
        row.workspace_name = str(body["workspace_name"]).strip()[:120]
    if body.get("product_name"):
        row.product_name = str(body["product_name"]).strip()[:120]
    if "seller_name" in body:
        row.seller_name = str(body.get("seller_name") or "").strip()[:160]
    if "offering" in body:
        row.offering = str(body.get("offering") or "").strip()[:500]
    if "ideal_customer" in body:
        row.ideal_customer = str(body.get("ideal_customer") or "").strip()[:300]
    _apply_icp(row, body)
    if body.get("currency"):
        row.currency = str(body["currency"]).strip()[:8]
    if body.get("retention_days") is not None:
        row.retention_days = max(1, int(body["retention_days"]))
    record(db, user=actor, action="settings_change", module="settings", target="workspace", detail={"workspace_name": row.workspace_name})
    db.commit()
    return _public(row)


@router.get("/geo")
def get_geo(db: Session = Depends(get_db), _user=Depends(require_module("geo"))):
    row = _settings(db)
    return {
        "country": row.country or "",
        "state": row.state or "",
        "district": row.district or "",
        "city": row.city or "",
        "postal_code": row.postal_code or "",
        "radius_km": row.radius_km,
    }


@router.put("/geo")
def put_geo(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("geo", manage=True))):
    row = _settings(db)
    for field in ("country", "state", "district", "city", "postal_code"):
        if field in body:
            setattr(row, field, str(body.get(field) or "").strip()[:80])
    if "radius_km" in body:
        raw = body.get("radius_km")
        row.radius_km = int(raw) if raw not in (None, "") else None
    record(
        db,
        user=actor,
        action="settings_change",
        module="geo",
        target="geographic_target",
        detail={"country": row.country, "state": row.state, "city": row.city, "postal_code": row.postal_code},
    )
    db.commit()
    return {
        "country": row.country,
        "state": row.state,
        "district": row.district,
        "city": row.city,
        "postal_code": row.postal_code,
        "radius_km": row.radius_km,
    }
