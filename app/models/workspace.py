"""Single-row workspace preferences, including the default geographic target."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import utcnow


class WorkspaceSettings(Base):
    __tablename__ = "workspace_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_name: Mapped[str] = mapped_column(String(120), default="LinkTMS")
    product_name: Mapped[str] = mapped_column(String(120), default="CanberraAI LeadPilot")
    seller_name: Mapped[str] = mapped_column(String(160), default="LinkTMS")
    offering: Mapped[str] = mapped_column(String(500), default="We help companies staff critical roles without a long search cycle.")
    ideal_customer: Mapped[str] = mapped_column(
        String(300),
        default="US companies hiring for US-based roles that want to hire, or are open to, recruitment vendors and staffing agencies.",
    )
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    retention_days: Mapped[int] = mapped_column(Integer, default=365)
    country: Mapped[str] = mapped_column(String(80), default="")
    state: Mapped[str] = mapped_column(String(80), default="")
    district: Mapped[str] = mapped_column(String(80), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    postal_code: Mapped[str] = mapped_column(String(20), default="")
    radius_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    icp_country: Mapped[str] = mapped_column(String(80), default="United States")
    icp_states: Mapped[list] = mapped_column(JSON, default=list)
    icp_city: Mapped[str] = mapped_column(String(80), default="")
    icp_opportunity_type: Mapped[str] = mapped_column(String(160), default="Staffing/recruitment RFP or bid")
    icp_buyer_type: Mapped[str] = mapped_column(String(200), default="")
    icp_role_category: Mapped[str] = mapped_column(String(80), default="")
    icp_industry: Mapped[str] = mapped_column(String(160), default="")
    icp_company_size: Mapped[str] = mapped_column(String(40), default="")
    icp_posted_window: Mapped[str] = mapped_column(String(20), default="open")
    icp_min_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    icp_keywords: Mapped[str] = mapped_column(String(500), default='"staffing services" "agencies welcome"')
    mascot_character: Mapped[str] = mapped_column(String(40), default="hanuman")
    mascot_family_friendly: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
