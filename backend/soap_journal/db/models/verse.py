from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from soap_journal.db.base import Base


class Verse(Base):
    __tablename__ = "verses"
    __table_args__ = (UniqueConstraint("chapter_id", "number", name="uq_verses_chapter_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True, nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    is_red_letter: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
