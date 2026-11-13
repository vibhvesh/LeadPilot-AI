"""Encrypted provider keys, access rules, usage, and LLM routing."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import utcnow


class ProviderKey(Base):
    __tablename__ = "provider_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    ciphertext: Mapped[str] = mapped_column(Text)
    hint: Mapped[str] = mapped_column(String(20), default="")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProviderAccess(Base):
    __tablename__ = "provider_access"
    __table_args__ = (UniqueConstraint("provider", "role", "user_id", name="uq_provider_scope"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    role: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    daily_quota: Mapped[int] = mapped_column(Integer, default=25)
    monthly_quota: Mapped[int] = mapped_column(Integer, default=250)


class ProviderUsage(Base):
    __tablename__ = "provider_usage"
    __table_args__ = (UniqueConstraint("user_id", "provider", "period", "period_kind", name="uq_usage_period"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    period: Mapped[str] = mapped_column(String(10), index=True)
    period_kind: Mapped[str] = mapped_column(String(10))
    count: Mapped[int] = mapped_column(Integer, default=0)


class LLMConfig(Base):
    __tablename__ = "llm_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    primary_provider: Mapped[str] = mapped_column(String(40), default="auto")
    primary_model: Mapped[str] = mapped_column(String(120), default="")
    fallback_provider: Mapped[str] = mapped_column(String(40), default="")
    fallback_model: Mapped[str] = mapped_column(String(120), default="")
    temperature: Mapped[float] = mapped_column(Float, default=0.2)
    max_tokens: Mapped[int] = mapped_column(Integer, default=1200)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
