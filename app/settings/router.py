"""Workspace preferences and the default geographic target."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_module
from app.models import WorkspaceSettings

router = APIRouter(prefix="/api")


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
        "currency": row.currency,
        "retention_days": row.retention_days,
        "country": row.country or "",
        "state": row.state or "",
        "district": row.district or "",
        "city": row.city or "",
        "postal_code": row.postal_code or "",
        "radius_km": row.radius_km,
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
