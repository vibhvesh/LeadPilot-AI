"""Run the specialist pipeline for one lead."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.pipeline import list_runs, run_pipeline
from app.core.database import get_db
from app.core.deps import require_module

router = APIRouter(prefix="/api/agents")


@router.get("/runs")
def runs(lead_id: int | None = None, db: Session = Depends(get_db), _user=Depends(require_module("grokbot"))):
    return list_runs(db, lead_id=lead_id)


@router.post("/run")
def run(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("grokbot", manage=True))):
    return run_pipeline(db, actor, int(body.get("lead_id") or 0))
