"""Saved target profiles and search runs."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_module
from app.search.presets import catalog_payload, compose_query, create_preset, delete_preset, suggestions, update_preset
from app.search.service import delete_criteria, list_criteria, list_runs, run_saved_search, save_criteria

router = APIRouter(prefix="/api/search")


@router.get("/presets")
def get_presets(db: Session = Depends(get_db), _user=Depends(require_module("search"))):
    return catalog_payload(db)


@router.get("/suggestions")
def get_suggestions(q: str = "", db: Session = Depends(get_db), _user=Depends(require_module("search"))):
    return {"suggestions": suggestions(db, q)}


@router.post("/preview")
def preview_query(body: dict, _db: Session = Depends(get_db), _user=Depends(require_module("search"))):
    from app.search.presets import clean_criteria

    return {"query": compose_query(clean_criteria(body))}


@router.post("/presets")
def post_preset(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("settings", manage=True))):
    return create_preset(db, actor, body)


@router.put("/presets/{preset_id}")
def put_preset(preset_id: int, body: dict, db: Session = Depends(get_db), actor=Depends(require_module("settings", manage=True))):
    return update_preset(db, actor, preset_id, body)


@router.delete("/presets/{preset_id}")
def remove_preset(preset_id: int, db: Session = Depends(get_db), actor=Depends(require_module("settings", manage=True))):
    delete_preset(db, actor, preset_id)
    return {"deleted": preset_id}


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
