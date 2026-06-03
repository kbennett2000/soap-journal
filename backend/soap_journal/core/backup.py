"""Headless builder for the journal backup export (FORMAT version 1).

``build_backup`` queries one user's journal and assembles a ``BackupDocument``
that is byte-compatible with the mobile app's restore (see
``schemas/backup.py`` for the contract and its source of truth). This module is
pure data work — no FastAPI/HTTP concerns — mirroring the mobile's pure
``buildBackup`` split so it is trivially testable.

The four queries (entries, translation codes, tags, verse coordinates) are each
issued once and joined in Python keyed by ``entry_id`` — no N+1.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.db.models.book import Book
from soap_journal.db.models.chapter import Chapter
from soap_journal.db.models.entry import Entry
from soap_journal.db.models.entry_scripture_verse import EntryScriptureVerse
from soap_journal.db.models.entry_tag import EntryTag
from soap_journal.db.models.tag import Tag
from soap_journal.db.models.translation import Translation
from soap_journal.db.models.verse import Verse
from soap_journal.schemas.backup import BackupDocument, BackupEntry, BackupVerse


def _iso_z(dt: datetime) -> str:
    """Format a UTC instant as ISO-8601 with a trailing ``Z``.

    The SQLite dialect returns NAIVE datetimes on read even though the column is
    ``DateTime(timezone=True)`` and was written with ``datetime.now(UTC)``: the
    stored wall-clock is UTC but ``tzinfo is None``. Calling ``.astimezone(UTC)``
    on a naive value would make Python assume server-LOCAL time and shift it,
    silently corrupting the exported instant. So treat naive as UTC first — the
    same fix as ``core/sessions.py:_normalize``.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


async def build_backup(
    db: AsyncSession, user_id: int, exported_at: datetime
) -> BackupDocument:
    entries = (
        (
            await db.execute(
                select(Entry)
                .where(Entry.user_id == user_id)
                .order_by(Entry.created_at, Entry.id)
            )
        )
        .scalars()
        .all()
    )

    if not entries:
        return BackupDocument(exported_at=_iso_z(exported_at), entries=[])

    entry_ids = [e.id for e in entries]
    translation_ids = {e.scripture_translation_id for e in entries}

    # translation_id -> code
    code_by_translation = dict(
        (
            await db.execute(
                select(Translation.id, Translation.code).where(
                    Translation.id.in_(translation_ids)
                )
            )
        ).all()
    )

    # entry_id -> [tag name, ...] ordered by lower(name)
    tags_by_entry: dict[int, list[str]] = defaultdict(list)
    tag_rows = (
        await db.execute(
            select(EntryTag.entry_id, Tag.name)
            .join(Tag, Tag.id == EntryTag.tag_id)
            .where(EntryTag.entry_id.in_(entry_ids))
            .order_by(EntryTag.entry_id, func.lower(Tag.name).asc())
        )
    ).all()
    for entry_id, name in tag_rows:
        tags_by_entry[entry_id].append(name)

    # entry_id -> [BackupVerse, ...] ordered by (book_order_index, chapter, verse)
    verses_by_entry: dict[int, list[BackupVerse]] = defaultdict(list)
    verse_rows = (
        await db.execute(
            select(
                EntryScriptureVerse.entry_id,
                Book.order_index,
                Chapter.number,
                Verse.number,
            )
            .join(Verse, Verse.id == EntryScriptureVerse.verse_id)
            .join(Chapter, Chapter.id == Verse.chapter_id)
            .join(Book, Book.id == Chapter.book_id)
            .where(EntryScriptureVerse.entry_id.in_(entry_ids))
            .order_by(
                EntryScriptureVerse.entry_id,
                Book.order_index,
                Chapter.number,
                Verse.number,
            )
        )
    ).all()
    for entry_id, book_order_index, chapter_number, verse_number in verse_rows:
        verses_by_entry[entry_id].append(
            BackupVerse(
                book_order_index=book_order_index,
                chapter=chapter_number,
                verse=verse_number,
            )
        )

    backup_entries = [
        BackupEntry(
            title=entry.title,
            entry_date=entry.entry_date.isoformat(),
            scripture_ref=entry.scripture_ref,
            scripture_translation_code=code_by_translation[entry.scripture_translation_id],
            scripture_text=entry.scripture_text,
            observation=entry.observation,
            application=entry.application,
            prayer=entry.prayer,
            created_at=_iso_z(entry.created_at),
            updated_at=_iso_z(entry.updated_at),
            verses=verses_by_entry[entry.id],
            tags=tags_by_entry[entry.id],
        )
        for entry in entries
    ]

    return BackupDocument(exported_at=_iso_z(exported_at), entries=backup_entries)
