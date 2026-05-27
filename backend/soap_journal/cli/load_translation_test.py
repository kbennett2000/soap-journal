"""Tests for the load-translation CLI."""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.cli.load_translation import (
    load_canonical_translation,
    load_translation_command,
)
from soap_journal.core.bible.books import ALL_BOOKS
from soap_journal.db.models.book import Book
from soap_journal.db.models.chapter import Chapter
from soap_journal.db.models.footnote import Footnote
from soap_journal.db.models.heading import Heading
from soap_journal.db.models.translation import Translation
from soap_journal.db.models.verse import Verse
from soap_journal.parsers.schema import (
    CanonicalBook,
    CanonicalChapter,
    CanonicalFootnote,
    CanonicalHeading,
    CanonicalTranslation,
    CanonicalVerse,
)


@pytest_asyncio.fixture(loop_scope="session")
async def clean_translations(db_session: AsyncSession) -> AsyncSession:
    """Start each loader test with an empty translations table.

    The session-scoped `bsb_loaded` fixture (used by the reader API tests)
    commits BSB to the shared in-memory DB; without this fixture the loader
    tests' row-count assertions would depend on test ordering.
    Deletes here run inside the per-test transaction and roll back at
    teardown, so this never affects other tests' view of BSB.
    """
    for model in (Footnote, Heading, Verse, Chapter, Book, Translation):
        await db_session.execute(delete(model))
    await db_session.flush()
    return db_session


# ---- fixtures --------------------------------------------------------------


def _book(index: int, *, verse_count: int = 1, chapter_count: int = 1) -> CanonicalBook:
    spec = ALL_BOOKS[index - 1]
    return CanonicalBook(
        name=spec.name,
        abbreviation=spec.abbreviation,
        order_index=spec.order_index,
        chapters=[
            CanonicalChapter(
                number=c,
                verses=[
                    CanonicalVerse(number=v, text=f"{spec.name} {c}:{v}")
                    for v in range(1, verse_count + 1)
                ],
            )
            for c in range(1, chapter_count + 1)
        ],
    )


def _full_translation(
    code: str = "TST",
    name: str = "Test Translation",
    *,
    enrich_genesis: bool = False,
) -> CanonicalTranslation:
    books = [_book(i) for i in range(1, 67)]
    if enrich_genesis:
        # Genesis 1: 5 verses with a heading + a footnote so we can verify
        # they're loaded too.
        books[0] = CanonicalBook(
            name=ALL_BOOKS[0].name,
            abbreviation=ALL_BOOKS[0].abbreviation,
            order_index=ALL_BOOKS[0].order_index,
            chapters=[
                CanonicalChapter(
                    number=1,
                    verses=[CanonicalVerse(number=v, text=f"Gen 1:{v}") for v in range(1, 6)],
                    headings=[CanonicalHeading(before_verse=1, text="The Creation")],
                    footnotes=[CanonicalFootnote(verse_number=2, text="Heb. tohu wabohu")],
                )
            ],
        )
    return CanonicalTranslation(
        code=code,
        name=name,
        language="en",
        copyright="© test fixture",
        books=books,
    )


# ---- core loader -----------------------------------------------------------


async def test_load_inserts_translation_books_chapters_verses(
    clean_translations: AsyncSession,
) -> None:
    db_session = clean_translations
    payload = _full_translation(enrich_genesis=True)
    books, chapters, verses = await load_canonical_translation(db_session, payload)

    # 65 other books contribute 1 verse each; Genesis 1 has 5.
    assert (books, chapters, verses) == (66, 66, 70)

    translation_row = (
        await db_session.execute(select(Translation).where(Translation.code == "TST"))
    ).scalar_one()
    assert translation_row.name == "Test Translation"
    assert translation_row.language == "en"

    book_count = (
        await db_session.execute(
            select(func.count()).select_from(Book).where(Book.translation_id == translation_row.id)
        )
    ).scalar_one()
    assert book_count == 66

    # Spot-check Genesis 1:2 — we enriched it above.
    text = (
        await db_session.execute(
            select(Verse.text)
            .join(Chapter, Chapter.id == Verse.chapter_id)
            .join(Book, Book.id == Chapter.book_id)
            .where(
                Book.translation_id == translation_row.id,
                Book.name == "Genesis",
                Chapter.number == 1,
                Verse.number == 2,
            )
        )
    ).scalar_one()
    assert text == "Gen 1:2"


async def test_loading_same_translation_twice_replaces_cleanly(
    clean_translations: AsyncSession,
) -> None:
    db_session = clean_translations
    first = _full_translation(code="TST", name="First name")
    second = _full_translation(code="TST", name="Renamed")

    await load_canonical_translation(db_session, first)
    await load_canonical_translation(db_session, second)

    translations = (
        (await db_session.execute(select(Translation).where(Translation.code == "TST")))
        .scalars()
        .all()
    )
    assert len(translations) == 1
    assert translations[0].name == "Renamed"

    # Row counts are unchanged after the replace.
    book_count = (await db_session.execute(select(func.count()).select_from(Book))).scalar_one()
    chapter_count = (
        await db_session.execute(select(func.count()).select_from(Chapter))
    ).scalar_one()
    verse_count = (await db_session.execute(select(func.count()).select_from(Verse))).scalar_one()
    assert (book_count, chapter_count, verse_count) == (66, 66, 66)


async def test_loading_second_translation_isolates_from_first(
    clean_translations: AsyncSession,
) -> None:
    db_session = clean_translations
    a = _full_translation(code="AAA", name="Alpha")
    b = _full_translation(code="BBB", name="Beta")

    await load_canonical_translation(db_session, a)
    await load_canonical_translation(db_session, b)

    # Two translations, each with 66 books.
    codes = sorted((await db_session.execute(select(Translation.code))).scalars().all())
    assert codes == ["AAA", "BBB"]

    total_books = (await db_session.execute(select(func.count()).select_from(Book))).scalar_one()
    assert total_books == 132  # 66 per translation

    # Deleting AAA via the loader pathway leaves BBB intact.
    a_again = _full_translation(code="AAA", name="Alpha renamed")
    await load_canonical_translation(db_session, a_again)

    bbb = (
        await db_session.execute(select(Translation).where(Translation.code == "BBB"))
    ).scalar_one()
    bbb_books = (
        await db_session.execute(
            select(func.count()).select_from(Book).where(Book.translation_id == bbb.id)
        )
    ).scalar_one()
    assert bbb_books == 66


# ---- CLI surface -----------------------------------------------------------


def test_cli_rejects_missing_file(tmp_path: Path) -> None:
    rc = load_translation_command(str(tmp_path / "nope.json"))
    assert rc == 2


def test_cli_rejects_invalid_canonical_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"code":"X","name":"X","language":"en","copyright":"x","books":[]}')
    rc = load_translation_command(str(bad))
    assert rc == 1


def test_invalid_canonical_payload_raises_validation_error() -> None:
    # Sanity check that our fixture validator covers obviously-broken input
    # (so the CLI's catch in test_cli_rejects_invalid_canonical_json is
    # exercising the right branch).
    with pytest.raises(ValidationError):
        CanonicalTranslation(code="X", name="X", language="en", copyright="x", books=[])
