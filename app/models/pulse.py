"""Industry headlines for the Industry Pulse page. Nothing here is published."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import utcnow

PULSE_STATUSES = ("open", "read", "dismissed")
PULSE_URGENCIES = ("urgent", "week", "fyi")
PULSE_SOURCES = ("news", "forum", "social")


class PulseItem(Base):
    __tablename__ = "pulse_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    headline: Mapped[str] = mapped_column(String(300), default="")
    why_it_matters: Mapped[str] = mapped_column(Text, default="")
    urgency: Mapped[str] = mapped_column(String(20), default="fyi", index=True)
    source_type: Mapped[str] = mapped_column(String(20), default="news", index=True)
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    url_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    links: Mapped[list] = mapped_column(JSON, default=list)
    topic: Mapped[str] = mapped_column(String(200), default="", index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    origin: Mapped[str] = mapped_column(String(40), default="manual")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PulseComment(Base):
    __tablename__ = "pulse_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("pulse_items.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
