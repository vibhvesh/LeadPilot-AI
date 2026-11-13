"""Run the specialist pipeline and leave qualification to a person."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.steps import enrich, orchestrate, outreach, qualify, quality, research
from app.audit.service import record
from app.core.errors import AppError
from app.models import AgentRun, Lead
from app.providers.llm import LLMClient
from app.settings.profile import load_profile


def run_pipeline(db: Session, actor, lead_id: int) -> dict:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise AppError("Lead not found", 404)
    profile = load_profile(db)
    llm = LLMClient(db, actor)
    steps = [orchestrate(lead), research(lead, llm, profile)]
    steps.append(enrich(db, lead))
    quality_step = quality(db, lead)
    steps.append(quality_step)
    qualification = qualify(lead, llm, quality_step, profile)
    steps.append(qualification)
    draft = outreach(lead, llm, qualification, profile)
    steps.append(draft)

    score = qualification["output"]["score"]
    recommend = qualification["output"]["recommend_qualify"]
    lead.score = score
    lead.qualification_summary = qualification["summary"]
    # The pipeline must not mark a lead qualified. A person does that in review.
    if lead.status == "Qualified" and not lead.human_reviewed:
        lead.status = "New"

    run = AgentRun(
        lead_id=lead.id,
        user_id=actor.id,
        status="completed",
        provider=llm.provider,
        model=llm.model,
        steps=steps,
        score=score,
        recommend_qualify=recommend,
        outreach_subject=draft["output"]["subject"],
        outreach_body=draft["output"]["body"],
        delivery="draft",
    )
    db.add(run)
    record(
        db,
        user=actor,
        action="agent_run",
        module="grokbot",
        target=str(lead.id),
        detail={"provider": llm.provider, "model": llm.model, "score": score, "recommend_qualify": recommend},
    )
    db.commit()
    db.refresh(run)
    db.refresh(lead)
    return serialize_run(run, lead.status)


def list_runs(db: Session, lead_id: int | None = None) -> list[dict]:
    statement = select(AgentRun).order_by(AgentRun.id.desc()).limit(30)
    if lead_id:
        statement = statement.where(AgentRun.lead_id == lead_id)
    runs = db.scalars(statement).all()
    return [serialize_run(run) for run in runs]


def serialize_run(run: AgentRun, lead_status: str | None = None) -> dict:
    return {
        "id": run.id,
        "lead_id": run.lead_id,
        "status": run.status,
        "provider": run.provider,
        "model": run.model,
        "score": run.score,
        "recommend_qualify": run.recommend_qualify,
        "delivery": run.delivery,
        "outreach": {"subject": run.outreach_subject, "body": run.outreach_body, "delivery": "draft"},
        "steps": run.steps or [],
        "lead_status": lead_status,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }
