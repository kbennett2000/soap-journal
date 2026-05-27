from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from soap_journal.db.base import Base


class EntryScriptureVerse(Base):
    """Per-verse linkage that powers the verse -> entries reverse lookup.

    Populated on every entry save from the parsed reference. The reverse
    direction (given a verse, find which entries cite it) is the next
    slice's reader endpoint; the index on verse_id keeps that cheap.
    """

    __tablename__ = "entry_scripture_verses"

    entry_id: Mapped[int] = mapped_column(
        ForeignKey("entries.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    verse_id: Mapped[int] = mapped_column(
        ForeignKey("verses.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
