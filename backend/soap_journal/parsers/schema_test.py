"""Tests for the canonical Bible JSON schema validators."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from soap_journal.core.bible.books import ALL_BOOKS
from soap_journal.parsers.schema import (
    CanonicalBook,
    CanonicalChapter,
    CanonicalFootnote,
    CanonicalHeading,
    CanonicalTranslation,
    CanonicalVerse,
)


def _minimal_chapter(number: int = 1, verse_count: int = 3) -> CanonicalChapter:
    return CanonicalChapter(
        number=number,
        verses=[CanonicalVerse(number=i, text=f"v{i}") for i in range(1, verse_count + 1)],
    )


def _book_for(index: int, verse_count: int = 1, chapter_count: int = 1) -> CanonicalBook:
    spec = ALL_BOOKS[index - 1]
    return CanonicalBook(
        name=spec.name,
        abbreviation=spec.abbreviation,
        order_index=spec.order_index,
        chapters=[_minimal_chapter(c, verse_count) for c in range(1, chapter_count + 1)],
    )


def _all_66_books_minimal() -> list[CanonicalBook]:
    return [_book_for(i) for i in range(1, 67)]


# ---- happy path ------------------------------------------------------------


def test_minimal_translation_validates() -> None:
    t = CanonicalTranslation(
        code="MIN",
        name="Minimal",
        language="en",
        copyright="© test",
        books=_all_66_books_minimal(),
    )
    assert len(t.books) == 66


def test_chapter_with_headings_and_footnotes_validates() -> None:
    chapter = CanonicalChapter(
        number=1,
        verses=[CanonicalVerse(number=i, text=f"v{i}") for i in (1, 2, 3)],
        headings=[CanonicalHeading(before_verse=1, text="Section A")],
        footnotes=[CanonicalFootnote(verse_number=2, text="see Ps 23")],
    )
    assert chapter.headings[0].before_verse == 1
    assert chapter.footnotes[0].verse_number == 2


def test_red_letter_defaults_false() -> None:
    v = CanonicalVerse(number=1, text="In the beginning")
    assert v.is_red_letter is False


# ---- chapter-level validators ---------------------------------------------


def test_verses_must_start_at_1() -> None:
    with pytest.raises(ValidationError, match="numbered 1..N"):
        CanonicalChapter(
            number=1,
            verses=[CanonicalVerse(number=2, text="x"), CanonicalVerse(number=3, text="y")],
        )


def test_verses_must_have_no_gaps() -> None:
    with pytest.raises(ValidationError, match="numbered 1..N"):
        CanonicalChapter(
            number=1,
            verses=[CanonicalVerse(number=1, text="x"), CanonicalVerse(number=3, text="z")],
        )


def test_verses_must_have_no_duplicates() -> None:
    with pytest.raises(ValidationError, match="numbered 1..N"):
        CanonicalChapter(
            number=1,
            verses=[
                CanonicalVerse(number=1, text="x"),
                CanonicalVerse(number=1, text="x-dup"),
            ],
        )


def test_heading_pointing_at_nonexistent_verse_rejected() -> None:
    with pytest.raises(ValidationError, match="does not match any verse"):
        CanonicalChapter(
            number=1,
            verses=[CanonicalVerse(number=1, text="x")],
            headings=[CanonicalHeading(before_verse=99, text="never")],
        )


def test_footnote_pointing_at_nonexistent_verse_rejected() -> None:
    with pytest.raises(ValidationError, match="does not match any verse"):
        CanonicalChapter(
            number=1,
            verses=[CanonicalVerse(number=1, text="x")],
            footnotes=[CanonicalFootnote(verse_number=42, text="never")],
        )


# ---- book-level validators -------------------------------------------------


def test_non_canonical_book_name_rejected() -> None:
    with pytest.raises(ValidationError, match="not the canonical form"):
        CanonicalBook(
            name="Genesys",
            abbreviation="Gen",
            order_index=1,
            chapters=[_minimal_chapter()],
        )


def test_alias_rejected_in_canonical_book_name_field() -> None:
    # "Song of Songs" is an alias, not the canonical name (which is "Song of
    # Solomon"). The parser should emit the canonical form.
    with pytest.raises(ValidationError, match="not the canonical form"):
        CanonicalBook(
            name="Song of Songs",
            abbreviation="Song",
            order_index=22,
            chapters=[_minimal_chapter()],
        )


def test_wrong_order_index_for_canonical_name_rejected() -> None:
    with pytest.raises(ValidationError, match="expects order_index=1"):
        CanonicalBook(
            name="Genesis",
            abbreviation="Gen",
            order_index=7,
            chapters=[_minimal_chapter()],
        )


def test_wrong_abbreviation_rejected() -> None:
    with pytest.raises(ValidationError, match="expects abbreviation"):
        CanonicalBook(
            name="Genesis",
            abbreviation="Gn",
            order_index=1,
            chapters=[_minimal_chapter()],
        )


def test_chapters_must_be_1_to_n() -> None:
    spec = ALL_BOOKS[0]
    with pytest.raises(ValidationError, match="chapters must be numbered 1..N"):
        CanonicalBook(
            name=spec.name,
            abbreviation=spec.abbreviation,
            order_index=spec.order_index,
            chapters=[_minimal_chapter(1), _minimal_chapter(3)],
        )


def test_duplicate_chapter_rejected() -> None:
    spec = ALL_BOOKS[0]
    with pytest.raises(ValidationError, match="chapters must be numbered 1..N"):
        CanonicalBook(
            name=spec.name,
            abbreviation=spec.abbreviation,
            order_index=spec.order_index,
            chapters=[_minimal_chapter(1), _minimal_chapter(1)],
        )


# ---- translation-level validators -----------------------------------------


def test_missing_book_rejected() -> None:
    books = _all_66_books_minimal()
    books.pop()  # drop Revelation
    with pytest.raises(ValidationError, match="must have exactly 66 books"):
        CanonicalTranslation(
            code="X",
            name="X",
            language="en",
            copyright="x",
            books=books,
        )


def test_out_of_order_books_rejected() -> None:
    books = _all_66_books_minimal()
    books[0], books[1] = books[1], books[0]  # swap Genesis and Exodus
    with pytest.raises(ValidationError, match="expected"):
        CanonicalTranslation(
            code="X",
            name="X",
            language="en",
            copyright="x",
            books=books,
        )


def test_unknown_field_rejected() -> None:
    # Models use extra="forbid".
    with pytest.raises(ValidationError):
        CanonicalVerse(number=1, text="x", unexpected=True)


def test_empty_text_rejected() -> None:
    with pytest.raises(ValidationError):
        CanonicalVerse(number=1, text="")
