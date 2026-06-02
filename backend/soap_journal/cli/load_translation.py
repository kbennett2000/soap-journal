"""Loader: canonical Bible JSON file -> database.

Usage:
    python -m soap_journal.cli load-translation <path.json>

Behavior:
- Validates the input against `CanonicalTranslation`. Validation failure
  exits non-zero with a helpful message and writes nothing.
- If a translation with the same `code` already exists, deletes it and
  every dependent row (cross_references -> footnotes -> verses -> headings
  -> chapters -> books -> translation) in dependency order — SQLite does not enforce
  ON DELETE CASCADE without PRAGMA foreign_keys=ON, so the loader does
  it explicitly. The replacement and the original delete share one
  transaction; a load that fails halfway rolls everything back.
- Prints a one-line summary on success.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from soap_journal.config import get_settings
from soap_journal.db.models.book import Book
from soap_journal.db.models.chapter import Chapter
from soap_journal.db.models.cross_reference import CrossReference
from soap_journal.db.models.footnote import Footnote
from soap_journal.db.models.heading import Heading
from soap_journal.db.models.translation import Translation
from soap_journal.db.models.verse import Verse
from soap_journal.parsers.schema import CanonicalCrossRef, CanonicalTranslation


async def _delete_existing_translation(db: AsyncSession, code: str) -> bool:
    """Delete a translation (and all dependent rows) by code if it exists.

    Returns True if a translation was deleted, False if there was nothing
    to delete. Walks the dependency tree explicitly because SQLite skips
    FK cascade enforcement by default.
    """
    result = await db.execute(select(Translation).where(Translation.code == code))
    existing = result.scalar_one_or_none()
    if existing is None:
        return False

    book_ids = [
        bid
        for (bid,) in (
            await db.execute(select(Book.id).where(Book.translation_id == existing.id))
        ).all()
    ]
    if book_ids:
        chapter_ids = [
            cid
            for (cid,) in (
                await db.execute(select(Chapter.id).where(Chapter.book_id.in_(book_ids)))
            ).all()
        ]
        if chapter_ids:
            verse_ids = [
                vid
                for (vid,) in (
                    await db.execute(select(Verse.id).where(Verse.chapter_id.in_(chapter_ids)))
                ).all()
            ]
            if verse_ids:
                # Cross-references reference both footnotes and verses of this
                # translation; delete them first so the footnote/verse deletes
                # below don't orphan rows or trip FKs. Every cross-ref's source
                # verse belongs to this translation, so scoping by from_verse_id
                # covers them all.
                await db.execute(
                    delete(CrossReference)
                    .where(CrossReference.from_verse_id.in_(verse_ids))
                    .execution_options(synchronize_session=False)
                )
                await db.execute(
                    delete(Footnote)
                    .where(Footnote.verse_id.in_(verse_ids))
                    .execution_options(synchronize_session=False)
                )
            await db.execute(
                delete(Verse)
                .where(Verse.chapter_id.in_(chapter_ids))
                .execution_options(synchronize_session=False)
            )
            await db.execute(
                delete(Heading)
                .where(Heading.chapter_id.in_(chapter_ids))
                .execution_options(synchronize_session=False)
            )
            await db.execute(
                delete(Chapter)
                .where(Chapter.book_id.in_(book_ids))
                .execution_options(synchronize_session=False)
            )
        await db.execute(
            delete(Book)
            .where(Book.translation_id == existing.id)
            .execution_options(synchronize_session=False)
        )
    await db.execute(
        delete(Translation)
        .where(Translation.id == existing.id)
        .execution_options(synchronize_session=False)
    )
    return True


async def _insert_translation(db: AsyncSession, payload: CanonicalTranslation) -> None:
    translation = Translation(
        code=payload.code,
        name=payload.name,
        language=payload.language,
        copyright_notice=payload.copyright,
    )
    db.add(translation)
    await db.flush()

    # Cross-ref targets are addressed by canonical book order (1..66) and may
    # point at a book inserted later than the note's own book (e.g. a Genesis
    # note referencing John), so resolve targets only after every book of this
    # translation exists. book_id_by_order maps order_index -> this
    # translation's Book.id; pending_cross_refs holds the inserted Footnote rows
    # (for their flushed id/verse_id) alongside their canonical cross-refs.
    book_id_by_order: dict[int, int] = {}
    pending_cross_refs: list[tuple[Footnote, list[CanonicalCrossRef]]] = []

    for canonical_book in payload.books:
        book = Book(
            translation_id=translation.id,
            name=canonical_book.name,
            abbreviation=canonical_book.abbreviation,
            order_index=canonical_book.order_index,
        )
        db.add(book)
        await db.flush()
        book_id_by_order[canonical_book.order_index] = book.id

        for canonical_chapter in canonical_book.chapters:
            chapter = Chapter(book_id=book.id, number=canonical_chapter.number)
            db.add(chapter)
            await db.flush()

            verse_rows: dict[int, Verse] = {}
            for canonical_verse in canonical_chapter.verses:
                verse = Verse(
                    chapter_id=chapter.id,
                    number=canonical_verse.number,
                    text=canonical_verse.text,
                    is_red_letter=canonical_verse.is_red_letter,
                )
                db.add(verse)
                verse_rows[canonical_verse.number] = verse
            await db.flush()

            for canonical_heading in canonical_chapter.headings:
                db.add(
                    Heading(
                        chapter_id=chapter.id,
                        before_verse=canonical_heading.before_verse,
                        text=canonical_heading.text,
                    )
                )

            for canonical_footnote in canonical_chapter.footnotes:
                verse_row = verse_rows[canonical_footnote.verse_number]
                footnote = Footnote(
                    verse_id=verse_row.id,
                    text=canonical_footnote.text,
                    note_type=canonical_footnote.note_type,
                    char_offset=canonical_footnote.char_offset,
                    marker=canonical_footnote.marker,
                    # ordinal is NOT NULL in the DB; a plain (unordered) footnote
                    # falls back to 0.
                    ordinal=(
                        canonical_footnote.ordinal if canonical_footnote.ordinal is not None else 0
                    ),
                )
                db.add(footnote)
                if canonical_footnote.cross_refs:
                    pending_cross_refs.append((footnote, canonical_footnote.cross_refs))

    # Flush so footnote ids are assigned before cross-references reference them.
    await db.flush()

    for footnote, cross_refs in pending_cross_refs:
        for cross_ref in cross_refs:
            db.add(
                CrossReference(
                    footnote_id=footnote.id,
                    from_verse_id=footnote.verse_id,
                    to_book_id=book_id_by_order[cross_ref.to_book_order_index],
                    to_chapter=cross_ref.to_chapter,
                    to_verse_start=cross_ref.to_verse_start,
                    to_verse_end=cross_ref.to_verse_end,
                )
            )

    await db.flush()


async def load_canonical_translation(
    db: AsyncSession, payload: CanonicalTranslation
) -> tuple[int, int, int]:
    """Replace-or-insert a translation. Returns (books, chapters, verses) counts.

    All writes share one transaction. The caller is responsible for
    committing (or rolling back). Wrap-and-commit lives in
    `load_translation_command` for the CLI path; tests own the transaction
    boundary themselves.
    """
    await _delete_existing_translation(db, payload.code)
    await _insert_translation(db, payload)
    return translation_counts(payload)


def translation_counts(payload: CanonicalTranslation) -> tuple[int, int, int]:
    """Count (books, chapters, verses) in a canonical payload.

    Shared by the loader and validator so both report the same numbers.
    """
    books = len(payload.books)
    chapters = sum(len(b.chapters) for b in payload.books)
    verses = sum(len(c.verses) for b in payload.books for c in b.chapters)
    return books, chapters, verses


async def _run_cli_load(path: Path) -> int:
    # One-shot CLI; sync I/O on a file we just opened is fine here.
    raw = path.read_text(encoding="utf-8")  # noqa: ASYNC240
    try:
        payload = CanonicalTranslation.model_validate_json(raw)
    except ValidationError as exc:
        print(f"error: canonical schema validation failed:\n{exc}", file=sys.stderr)
        return 1

    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(settings.database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with session_factory() as session:
            try:
                books, chapters, verses = await load_canonical_translation(session, payload)
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    finally:
        await engine.dispose()

    print(f"Loaded {payload.code}: {books} books, {chapters} chapters, {verses} verses")
    return 0


def load_translation_command(path_str: str) -> int:
    path = Path(path_str)
    if not path.exists():
        print(f"error: {path} does not exist", file=sys.stderr)
        return 2
    try:
        return asyncio.run(_run_cli_load(path))
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
