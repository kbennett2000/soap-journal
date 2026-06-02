"""Tests for the load-translation CLI."""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.cli.load_translation import (
    load_canonical_translation,
    load_translation_command,
)
from soap_journal.core.bible.books import ALL_BOOKS
from soap_journal.db.fts import BACKFILL_NOTES_FTS, BACKFILL_VERSES_FTS
from soap_journal.db.models.book import Book
from soap_journal.db.models.chapter import Chapter
from soap_journal.db.models.cross_reference import CrossReference
from soap_journal.db.models.footnote import Footnote
from soap_journal.db.models.heading import Heading
from soap_journal.db.models.translation import Translation
from soap_journal.db.models.verse import Verse
from soap_journal.parsers.schema import (
    CanonicalBook,
    CanonicalChapter,
    CanonicalCrossRef,
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
    for model in (CrossReference, Footnote, Heading, Verse, Chapter, Book, Translation):
        await db_session.execute(delete(model))
    # FTS5 virtual tables aren't ORM models, so clear them explicitly too.
    await db_session.execute(text("DELETE FROM verses_fts"))
    await db_session.execute(text("DELETE FROM notes_fts"))
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
    enrich_notes: bool = False,
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
    if enrich_notes:
        # Genesis 1 with a plain footnote (verse 2) and a rich, typed,
        # char-anchored note (verse 3) carrying a cross-ref to John 1:1 —
        # John lives in the same translation but is inserted much later, so
        # this exercises cross-book target resolution.
        books[0] = CanonicalBook(
            name=ALL_BOOKS[0].name,
            abbreviation=ALL_BOOKS[0].abbreviation,
            order_index=ALL_BOOKS[0].order_index,
            chapters=[
                CanonicalChapter(
                    number=1,
                    verses=[CanonicalVerse(number=v, text=f"Gen 1:{v}") for v in range(1, 6)],
                    footnotes=[
                        CanonicalFootnote(verse_number=2, text="a plain footnote"),
                        CanonicalFootnote(
                            verse_number=3,
                            text="tn The Hebrew term...",
                            note_type="tn",
                            char_offset=4,
                            marker=1,
                            ordinal=0,
                            cross_refs=[
                                CanonicalCrossRef(
                                    to_book_order_index=43,  # John
                                    to_chapter=1,
                                    to_verse_start=1,
                                ),
                            ],
                        ),
                    ],
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


# ---- rich notes + cross-references -----------------------------------------


async def _genesis_footnote(db: AsyncSession, translation_id: int, verse_number: int) -> Footnote:
    return (
        await db.execute(
            select(Footnote)
            .join(Verse, Verse.id == Footnote.verse_id)
            .join(Chapter, Chapter.id == Verse.chapter_id)
            .join(Book, Book.id == Chapter.book_id)
            .where(
                Book.translation_id == translation_id,
                Book.name == "Genesis",
                Chapter.number == 1,
                Verse.number == verse_number,
            )
        )
    ).scalar_one()


async def test_rich_note_columns_persist(clean_translations: AsyncSession) -> None:
    db_session = clean_translations
    payload = _full_translation(enrich_notes=True)
    await load_canonical_translation(db_session, payload)

    tid = (
        await db_session.execute(select(Translation.id).where(Translation.code == "TST"))
    ).scalar_one()
    fn = await _genesis_footnote(db_session, tid, verse_number=3)
    assert fn.text == "tn The Hebrew term..."
    assert fn.note_type == "tn"
    assert fn.char_offset == 4
    assert fn.marker == 1
    assert fn.ordinal == 0


async def test_plain_footnote_loads_with_null_note_fields(
    clean_translations: AsyncSession,
) -> None:
    db_session = clean_translations
    payload = _full_translation(enrich_notes=True)
    await load_canonical_translation(db_session, payload)

    tid = (
        await db_session.execute(select(Translation.id).where(Translation.code == "TST"))
    ).scalar_one()
    plain = await _genesis_footnote(db_session, tid, verse_number=2)
    assert plain.text == "a plain footnote"
    assert plain.note_type is None
    assert plain.char_offset is None
    assert plain.marker is None
    # ordinal is NOT NULL in the DB and falls back to 0 for unordered notes.
    assert plain.ordinal == 0


async def test_cross_reference_persists_and_links_source(
    clean_translations: AsyncSession,
) -> None:
    db_session = clean_translations
    payload = _full_translation(enrich_notes=True)
    await load_canonical_translation(db_session, payload)

    tid = (
        await db_session.execute(select(Translation.id).where(Translation.code == "TST"))
    ).scalar_one()
    rich = await _genesis_footnote(db_session, tid, verse_number=3)

    xrefs = (await db_session.execute(select(CrossReference))).scalars().all()
    assert len(xrefs) == 1
    xr = xrefs[0]

    john_id = (
        await db_session.execute(
            select(Book.id).where(Book.translation_id == tid, Book.name == "John")
        )
    ).scalar_one()
    assert xr.footnote_id == rich.id
    assert xr.from_verse_id == rich.verse_id  # denormalized source verse
    assert xr.to_book_id == john_id
    assert (xr.to_chapter, xr.to_verse_start, xr.to_verse_end) == (1, 1, None)


async def test_cross_reference_resolves_book_within_its_own_translation(
    clean_translations: AsyncSession,
) -> None:
    db_session = clean_translations
    # Two translations, each with a Genesis->John cross-ref. Each cross-ref's
    # target John must be the John of the SAME translation as its source verse.
    await load_canonical_translation(db_session, _full_translation(code="AAA", enrich_notes=True))
    await load_canonical_translation(db_session, _full_translation(code="BBB", enrich_notes=True))

    xrefs = (await db_session.execute(select(CrossReference))).scalars().all()
    assert len(xrefs) == 2
    for xr in xrefs:
        source_tid = (
            await db_session.execute(
                select(Book.translation_id)
                .join(Chapter, Chapter.book_id == Book.id)
                .join(Verse, Verse.chapter_id == Chapter.id)
                .where(Verse.id == xr.from_verse_id)
            )
        ).scalar_one()
        target_book = (
            await db_session.execute(select(Book).where(Book.id == xr.to_book_id))
        ).scalar_one()
        assert target_book.translation_id == source_tid
        assert target_book.name == "John"


async def test_reload_replaces_cross_references_cleanly(
    clean_translations: AsyncSession,
) -> None:
    db_session = clean_translations
    await load_canonical_translation(db_session, _full_translation(code="TST", enrich_notes=True))
    await load_canonical_translation(db_session, _full_translation(code="TST", enrich_notes=True))

    # The delete walk removes cross_references ahead of footnotes/verses, so a
    # replace-load leaves exactly one cross-ref (no orphans, no FK error).
    xref_count = (
        await db_session.execute(select(func.count()).select_from(CrossReference))
    ).scalar_one()
    assert xref_count == 1

    footnote_count = (
        await db_session.execute(select(func.count()).select_from(Footnote))
    ).scalar_one()
    assert footnote_count == 2  # one plain + one rich


# ---- FTS5 search index (ADR-0003 Cycle 1) ----------------------------------


async def _fts_count(db: AsyncSession, table: str, tid: int | None = None) -> int:
    sql = f"SELECT count(*) FROM {table}"
    params: dict[str, int] = {}
    if tid is not None:
        sql += " WHERE translation_id = :tid"
        params["tid"] = tid
    return (await db.execute(text(sql), params)).scalar_one()


async def _match_count(db: AsyncSession, table: str, term: str) -> int:
    # table is a trusted literal; the search term is bound.
    sql = f"SELECT count(*) FROM {table} WHERE {table} MATCH :q"  # noqa: S608
    return (await db.execute(text(sql), {"q": term})).scalar_one()


async def test_load_populates_fts_tables(clean_translations: AsyncSession) -> None:
    db_session = clean_translations
    await load_canonical_translation(db_session, _full_translation(enrich_notes=True))
    tid = (
        await db_session.execute(select(Translation.id).where(Translation.code == "TST"))
    ).scalar_one()

    # Genesis 1 has 5 verses; the other 65 books contribute 1 each = 70.
    assert await _fts_count(db_session, "verses_fts", tid) == 70
    # Two footnotes on Genesis 1 (a plain one + a typed 'tn').
    assert await _fts_count(db_session, "notes_fts", tid) == 2

    # note_type is carried on notes_fts (one typed 'tn', one plain NULL).
    types = (
        (await db_session.execute(text("SELECT note_type FROM notes_fts ORDER BY note_type")))
        .scalars()
        .all()
    )
    assert "tn" in types

    # MATCH works: the rich note body ("tn The Hebrew term...") is searchable,
    # and a verse from another book ("Exodus 1:1") matches on its book word.
    assert await _match_count(db_session, "notes_fts", "hebrew") == 1
    assert await _match_count(db_session, "verses_fts", "exodus") == 1


async def test_reload_replaces_fts_rows_cleanly(clean_translations: AsyncSession) -> None:
    db_session = clean_translations
    await load_canonical_translation(db_session, _full_translation(code="TST", enrich_notes=True))
    await load_canonical_translation(db_session, _full_translation(code="TST", enrich_notes=True))

    # Teardown-first means the second load replaced, not doubled: global counts
    # equal a single translation's contribution (70 verses, 2 notes).
    assert await _fts_count(db_session, "verses_fts") == 70
    assert await _fts_count(db_session, "notes_fts") == 2


async def test_plain_translation_populates_verses_not_notes(
    clean_translations: AsyncSession,
) -> None:
    db_session = clean_translations
    # No enrich flags => 66 books x 1 verse, zero footnotes.
    await load_canonical_translation(db_session, _full_translation())
    tid = (
        await db_session.execute(select(Translation.id).where(Translation.code == "TST"))
    ).scalar_one()
    assert await _fts_count(db_session, "verses_fts", tid) == 66
    assert await _fts_count(db_session, "notes_fts", tid) == 0


async def test_fts_teardown_is_scoped_to_one_translation(
    clean_translations: AsyncSession,
) -> None:
    db_session = clean_translations
    await load_canonical_translation(db_session, _full_translation(code="AAA", enrich_notes=True))
    await load_canonical_translation(db_session, _full_translation(code="BBB", enrich_notes=True))
    bbb = (
        await db_session.execute(select(Translation.id).where(Translation.code == "BBB"))
    ).scalar_one()

    # Reloading AAA must not touch BBB's FTS rows (teardown is per translation_id).
    await load_canonical_translation(db_session, _full_translation(code="AAA", enrich_notes=True))
    assert await _fts_count(db_session, "verses_fts", bbb) == 70
    assert await _fts_count(db_session, "notes_fts", bbb) == 2
    # Two translations' worth of FTS rows in total, no orphans.
    assert await _fts_count(db_session, "verses_fts") == 140
    assert await _fts_count(db_session, "notes_fts") == 4


async def test_migration_backfill_makes_existing_rows_searchable(
    clean_translations: AsyncSession,
) -> None:
    # Simulate a pre-migration DB: verses/footnotes present but FTS empty, then
    # run the exact backfill SQL the Alembic migration uses and confirm the
    # rows become searchable. (Guards the silent-failure trap for the bundled
    # translations that predate the FTS tables.)
    db_session = clean_translations
    await load_canonical_translation(db_session, _full_translation(enrich_notes=True))

    await db_session.execute(text("DELETE FROM verses_fts"))
    await db_session.execute(text("DELETE FROM notes_fts"))
    assert await _fts_count(db_session, "verses_fts") == 0
    assert await _fts_count(db_session, "notes_fts") == 0

    await db_session.execute(text(BACKFILL_VERSES_FTS))
    await db_session.execute(text(BACKFILL_NOTES_FTS))

    assert await _fts_count(db_session, "verses_fts") == 70
    assert await _fts_count(db_session, "notes_fts") == 2
    # Searchable again after the backfill.
    assert await _match_count(db_session, "verses_fts", "exodus") == 1


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
