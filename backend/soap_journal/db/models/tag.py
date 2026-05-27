from datetime import datetime, timezone

from sqlalchemy import Computed, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from soap_journal.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("user_id", "name_lower", name="uq_tags_user_name_lower"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    # Stored generated column so case-insensitive uniqueness is enforced at
    # the DB layer without losing the original casing on `name`. Two users
    # may each have "Faith"; one user can't have both "Faith" and "FAITH".
    name_lower: Mapped[str] = mapped_column(
        String(50),
        Computed("lower(name)", persisted=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
