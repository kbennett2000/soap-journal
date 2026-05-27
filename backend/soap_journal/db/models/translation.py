from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from soap_journal.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Translation(Base):
    __tablename__ = "translations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    copyright_notice: Mapped[str] = mapped_column(String, nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
