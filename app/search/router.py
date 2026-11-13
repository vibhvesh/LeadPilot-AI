"""Saved target profiles and search runs."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_module
from app.search.service import delete_criteria, list_criteria, list_runs, run_saved_search, save_criteria

router = APIRouter(prefix="/api/search")


@router.get("/criteria")
def get_criteria(db: Session = Depends(get_db), _user=Depends(require_module("search"))):
    return list_criteria(db)


@router.post("/criteria")
def post_criteria(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("search", manage=True))):
    return save_criteria(db, actor, body)


@router.delete("/criteria/{criteria_id}")
def remove_criteria(criteria_id: int, db: Session = Depends(get_db), actor=Depends(require_module("search", manage=True))):
    delete_criteria(db, actor, criteria_id)
    return {"deleted": criteria_id}


@router.post("/criteria/{criteria_id}/run")
def run_criteria(criteria_id: int, db: Session = Depends(get_db), actor=Depends(require_module("search", manage=True))):
    return run_saved_search(db, actor, criteria_id)


@router.get("/runs")
def runs(db: Session = Depends(get_db), _user=Depends(require_module("search"))):
    return list_runs(db)
