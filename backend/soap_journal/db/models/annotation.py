from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from soap_journal.db.base import Base

# The six highlight colors (matches the reader palette). Enforced both here (DB
# CHECK) and in the Pydantic schema.
ANNOTATION_COLORS = ("yellow", "green", "blue", "pink", "orange", "purple")


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Annotation(Base):
    """A user's highlight (optionally with a note) over a span of verse text.

    Anchored by canonical coordinates + the translation *code*, deliberately
    WITHOUT a foreign key to `verses` or `translations`: the loader replace-loads
    a translation (delete + insert), so those rows' ids churn on every reload and
    an FK would orphan or cascade-delete a user's highlights. The canonical
    coords + stable code survive reloads. Only `user_id` is a real FK. See
    docs/adr/0005-annotation-highlight-layer.md.
    """

    __tablename__ = "annotations"
    __table_args__ = (
        CheckConstraint(
            "color IN ('yellow', 'green', 'blue', 'pink', 'orange', 'purple')",
            name="ck_annotations_color",
        ),
        # The reader's per-chapter fetch: this user's highlights for one
        # translation/book/chapter.
        Index(
            "ix_annotations_user_lookup",
            "user_id",
            "translation_code",
            "book",
            "chapter",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # translation_code is a plain string, NOT a FK to translations — see the
    # class docstring. Likewise book/verse/char are plain ints, no FK to verses.
    translation_code: Mapped[str] = mapped_column(String(16), nullable=False)
    book: Mapped[str] = mapped_column(String, nullable=False)  # canonical book name
    chapter: Mapped[int] = mapped_column(Integer, nullable=False)
    verse_start: Mapped[int] = mapped_column(Integer, nullable=False)
    verse_end: Mapped[int] = mapped_column(Integer, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
