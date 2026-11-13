"""Score a lead with the same rules the qualification agent uses."""

from app.agents.steps import heuristic_score, qualify, quality
from app.providers.llm import LLMClient, select_provider
from app.settings.profile import load_profile


def apply_score(db, actor, lead) -> int:
    quality_step = quality(db, lead)
    provider, _model, _note = select_provider(db)
    profile = load_profile(db)
    if provider == "mock":
        score = heuristic_score(lead, quality_step["output"])
        lead.score = score
        if not lead.qualification_summary:
            lead.qualification_summary = (lead.why_fit or f"Score {score}.")[:500]
        return score
    result = qualify(lead, LLMClient(db, actor), quality_step, profile)
    lead.score = result["output"]["score"]
    lead.qualification_summary = result["summary"]
    return lead.score
