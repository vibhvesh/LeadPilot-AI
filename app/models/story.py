"""Admin-edited lines for the Ramayana story overlay."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.identity import utcnow


class StoryMessage(Base):
    __tablename__ = "story_messages"
    __table_args__ = (UniqueConstraint("scene_id", "actor", name="uq_story_message"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    scene_id: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(Text, default="")
    updated_by: Mapped[str] = mapped_column(String(160), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
