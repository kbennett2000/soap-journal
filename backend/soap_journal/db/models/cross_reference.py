from sqlalchemy import ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from soap_journal.db.base import Base


class CrossReference(Base):
    """A cross-reference contained in a note, pointing at a verse (or range).

    The target is stored as a book id (resolved to the *same translation* at
    load time) plus chapter and verse numbers — not a resolved verse row, since
    targets may be ranges and may not all resolve. `from_verse_id` is kept
    denormalized (it equals the owning footnote's verse) to power the future
    verse -> references reverse lookup without a join through footnotes.
    """

    __tablename__ = "cross_references"
    __table_args__ = (
        Index(
            "ix_cross_references_to_target",
            "to_book_id",
            "to_chapter",
            "to_verse_start",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    footnote_id: Mapped[int] = mapped_column(
        ForeignKey("footnotes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    from_verse_id: Mapped[int] = mapped_column(
        ForeignKey("verses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    to_book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False
    )
    to_chapter: Mapped[int] = mapped_column(Integer, nullable=False)
    to_verse_start: Mapped[int] = mapped_column(Integer, nullable=False)
    to_verse_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
