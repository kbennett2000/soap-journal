from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from soap_journal.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Entry(Base):
    __tablename__ = "entries"
    __table_args__ = (
        # The dashboard's recent-entries query is "this user, most recent
        # first." A compound index on (user_id, entry_date DESC) serves it
        # without a separate sort step.
        Index("ix_entries_user_date_desc", "user_id", "entry_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    entry_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    scripture_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    scripture_translation_id: Mapped[int] = mapped_column(
        # RESTRICT on translations: an admin cannot delete a translation that
        # entries reference. Translation deletion isn't an endpoint in v1;
        # the constraint encodes the intent.
        ForeignKey("translations.id", ondelete="RESTRICT"), nullable=False
    )
    scripture_text: Mapped[str] = mapped_column(Text, nullable=False)
    observation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    application: Mapped[str] = mapped_column(Text, nullable=False, default="")
    prayer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
