"""Natural-language lead search."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai_search.runner import list_runs, run_ai_search, source_counts
from app.core.database import get_db
from app.core.deps import require_module

router = APIRouter(prefix="/api/search")


@router.post("/ai")
def post_ai_search(body: dict, db: Session = Depends(get_db), actor=Depends(require_module("search", manage=True))):
    rounds = body.get("rounds")
    criteria = body.get("criteria") if isinstance(body.get("criteria"), dict) else None
    return run_ai_search(db, actor, str(body.get("text") or ""), rounds=int(rounds) if rounds else None, criteria=criteria)


@router.get("/ai")
def get_ai_search(db: Session = Depends(get_db), _user=Depends(require_module("search"))):
    return {"runs": list_runs(db), "sources": source_counts(db)}
