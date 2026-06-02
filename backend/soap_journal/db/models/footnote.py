from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from soap_journal.db.base import Base


class Footnote(Base):
    __tablename__ = "footnotes"
    __table_args__ = (
        # note_type is a typed-note category (tn/sn/tc/map) or NULL for a plain
        # footnote. `IN (...)` evaluates to NULL (not false) for NULL, so this
        # constraint also permits unset note_type.
        CheckConstraint(
            "note_type IN ('tn', 'sn', 'tc', 'map')",
            name="ck_footnotes_note_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    verse_id: Mapped[int] = mapped_column(
        ForeignKey("verses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    text: Mapped[str] = mapped_column(String, nullable=False)
    # Rich-note fields (NULL/0 for the bundled plain-footnote translations).
    note_type: Mapped[str | None] = mapped_column(String, nullable=True)
    char_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    marker: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
