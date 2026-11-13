"""Score a lead with the qualification agent. A missing model is reported, not guessed."""

from app.agents.steps import qualify, quality
from app.providers.llm import LLMClient
from app.settings.profile import load_profile


def apply_score(db, actor, lead) -> int:
    quality_step = quality(db, lead)
    profile = load_profile(db)
    result = qualify(lead, LLMClient(db, actor), quality_step, profile)
    lead.score = result["output"]["score"]
    lead.qualification_summary = result["summary"]
    return lead.score
