"""Public social posts for the Social page. These rows are never published anywhere."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import utcnow

SOCIAL_STATUSES = ("open", "done", "ignored")
SOCIAL_BUCKETS = ("reply", "engage", "fyi")


class SocialItem(Base):
    __tablename__ = "social_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(40), default="other", index=True)
    post_url: Mapped[str] = mapped_column(String(1000), default="")
    url_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    poster_name: Mapped[str] = mapped_column(String(250), default="")
    poster_role: Mapped[str] = mapped_column(String(250), default="")
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    snippet: Mapped[str] = mapped_column(Text, default="")
    topic: Mapped[str] = mapped_column(String(200), default="", index=True)
    company: Mapped[str] = mapped_column(String(250), default="", index=True)
    discussion_key: Mapped[str] = mapped_column(String(200), default="", index=True)
    bucket: Mapped[str] = mapped_column(String(20), default="fyi", index=True)
    why_it_matters: Mapped[str] = mapped_column(Text, default="")
    suggested_reply: Mapped[str] = mapped_column(Text, default="")
    work_auth: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    source: Mapped[str] = mapped_column(String(40), default="manual")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SocialComment(Base):
    __tablename__ = "social_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("social_items.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
