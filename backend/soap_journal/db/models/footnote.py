from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from soap_journal.db.base import Base


class Footnote(Base):
    __tablename__ = "footnotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    verse_id: Mapped[int] = mapped_column(
        ForeignKey("verses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    text: Mapped[str] = mapped_column(String, nullable=False)
