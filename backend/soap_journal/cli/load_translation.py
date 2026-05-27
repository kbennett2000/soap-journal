"""Loader: canonical Bible JSON file -> database.

Usage:
    python -m soap_journal.cli load-translation <path.json>

Behavior:
- Validates the input against `CanonicalTranslation`. Validation failure
  exits non-zero with a helpful message and writes nothing.
- If a translation with the same `code` already exists, deletes it and
  every dependent row (footnotes -> verses -> headings -> chapters ->
  books -> translation) in dependency order — SQLite does not enforce
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
from soap_journal.db.models.footnote import Footnote
from soap_journal.db.models.heading import Heading
from soap_journal.db.models.translation import Translation
from soap_journal.db.models.verse import Verse
from soap_journal.parsers.schema import CanonicalTranslation


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
                    await db.execute(
                        select(Verse.id).where(Verse.chapter_id.in_(chapter_ids))
                    )
                ).all()
            ]
            if verse_ids:
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

    for canonical_book in payload.books:
        book = Book(
            translation_id=translation.id,
            name=canonical_book.name,
            abbreviation=canonical_book.abbreviation,
            order_index=canonical_book.order_index,
        )
        db.add(book)
        await db.flush()

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
                db.add(Footnote(verse_id=verse_row.id, text=canonical_footnote.text))

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

    books = len(payload.books)
    chapters = sum(len(b.chapters) for b in payload.books)
    verses = sum(len(c.verses) for b in payload.books for c in b.chapters)
    return books, chapters, verses


async def _run_cli_load(path: Path) -> int:
    raw = path.read_text(encoding="utf-8")
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

    print(
        f"Loaded {payload.code}: {books} books, {chapters} chapters, {verses} verses"
    )
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
