"""Dashboard, pipeline, and report endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_module
from app.dashboard.service import dashboard, pipeline, reports

router = APIRouter(prefix="/api")


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db), actor=Depends(require_module("dashboard"))):
    return dashboard(db, actor)


@router.get("/pipeline")
def get_pipeline(db: Session = Depends(get_db), _user=Depends(require_module("pipeline"))):
    return pipeline(db)


@router.get("/reports")
def get_reports(db: Session = Depends(get_db), _user=Depends(require_module("reports"))):
    return reports(db)
