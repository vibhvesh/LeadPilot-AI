"""Saved search profiles and the runs that create leads."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import utcnow


class SearchCriteria(Base):
    __tablename__ = "search_criteria"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    industry: Mapped[str] = mapped_column(String(160), default="")
    keywords: Mapped[str] = mapped_column(String(500), default="")
    company_size: Mapped[str] = mapped_column(String(40), default="")
    country: Mapped[str] = mapped_column(String(80), default="")
    state: Mapped[str] = mapped_column(String(80), default="")
    district: Mapped[str] = mapped_column(String(80), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    postal_code: Mapped[str] = mapped_column(String(20), default="")
    radius_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    results_limit: Mapped[int] = mapped_column(Integer, default=10)
    states: Mapped[list] = mapped_column(JSON, default=list)
    opportunity_type: Mapped[str] = mapped_column(String(160), default="")
    buyer_type: Mapped[str] = mapped_column(String(200), default="")
    role_category: Mapped[str] = mapped_column(String(80), default="")
    posted_window: Mapped[str] = mapped_column(String(20), default="")
    min_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    query_templates: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SearchPreset(Base):
    """Admin-editable search chip. Seeded from the registry, then stored here."""

    __tablename__ = "search_presets"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    label: Mapped[str] = mapped_column(String(160))
    country: Mapped[str] = mapped_column(String(80), default="United States")
    states: Mapped[list] = mapped_column(JSON, default=list)
    city: Mapped[str] = mapped_column(String(80), default="")
    opportunity_type: Mapped[str] = mapped_column(String(160), default="")
    buyer_type: Mapped[str] = mapped_column(String(200), default="")
    role_category: Mapped[str] = mapped_column(String(80), default="")
    industry: Mapped[str] = mapped_column(String(160), default="")
    company_size: Mapped[str] = mapped_column(String(40), default="")
    posted_window: Mapped[str] = mapped_column(String(20), default="")
    min_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    keywords: Mapped[str] = mapped_column(String(500), default="")
    query_templates: Mapped[list] = mapped_column(JSON, default=list)
    ai_text: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AiSearchRun(Base):
    __tablename__ = "ai_search_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    plan: Mapped[dict] = mapped_column(JSON, default=dict)
    rounds: Mapped[int] = mapped_column(Integer, default=1)
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    providers: Mapped[list] = mapped_column(JSON, default=list)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class SearchRun(Base):
    __tablename__ = "search_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    criteria_id: Mapped[int | None] = mapped_column(ForeignKey("search_criteria.id"), nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), default="")
    query: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="completed")
    fetched: Mapped[int] = mapped_column(Integer, default=0)
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
