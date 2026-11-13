"""Workspace business profile used by agent and search prompts."""

from sqlalchemy.orm import Session

from app.models import WorkspaceSettings

DEFAULT_SELLER = "LinkTMS"
DEFAULT_OFFERING = "We help companies staff critical roles without a long search cycle."
DEFAULT_CUSTOMER = (
    "US companies hiring for US-based roles that want to hire, or are open to, "
    "recruitment vendors and staffing agencies."
)
DEFAULT_PRODUCT = "CanberraAI LeadPilot"


def load_profile(db: Session) -> dict:
    row = db.get(WorkspaceSettings, 1)
    return {
        "seller_name": (getattr(row, "seller_name", None) or DEFAULT_SELLER)[:160],
        "offering": (getattr(row, "offering", None) or DEFAULT_OFFERING)[:500],
        "ideal_customer": (getattr(row, "ideal_customer", None) or DEFAULT_CUSTOMER)[:300],
        "product_name": (getattr(row, "product_name", None) or DEFAULT_PRODUCT)[:120],
    }


def profile_brief(profile: dict | None) -> str:
    data = profile or {}
    seller = data.get("seller_name") or DEFAULT_SELLER
    offering = data.get("offering") or DEFAULT_OFFERING
    customer = data.get("ideal_customer") or DEFAULT_CUSTOMER
    return f"Seller: {seller}. What we sell: {offering} Ideal customer: {customer}."
