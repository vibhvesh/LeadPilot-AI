"""Single-row workspace preferences, including the default geographic target."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import utcnow


class WorkspaceSettings(Base):
    __tablename__ = "workspace_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_name: Mapped[str] = mapped_column(String(120), default="LinkTMS")
    product_name: Mapped[str] = mapped_column(String(120), default="CanberraAI LeadPilot")
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    retention_days: Mapped[int] = mapped_column(Integer, default=365)
    country: Mapped[str] = mapped_column(String(80), default="")
    state: Mapped[str] = mapped_column(String(80), default="")
    district: Mapped[str] = mapped_column(String(80), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    postal_code: Mapped[str] = mapped_column(String(20), default="")
    radius_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
