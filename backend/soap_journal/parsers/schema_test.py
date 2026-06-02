"""Tests for the canonical Bible JSON schema validators."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from soap_journal.core.bible.books import ALL_BOOKS
from soap_journal.parsers.schema import (
    CanonicalBook,
    CanonicalChapter,
    CanonicalCrossRef,
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


# ---- notes enrichment: backward compatibility ------------------------------


def test_plain_footnote_leaves_new_fields_unset() -> None:
    # An untyped footnote (every bundled translation) must default the new
    # fields and validate unchanged.
    fn = CanonicalFootnote(verse_number=1, text="see Ps 23")
    assert fn.note_type is None
    assert fn.char_offset is None
    assert fn.marker is None
    assert fn.ordinal is None
    assert fn.cross_refs == []


def test_existing_canonical_json_validates_unchanged() -> None:
    # JSON with no note metadata (the shape every bundled parser emits) still
    # round-trips through the enriched schema.
    raw = (
        '{"number": 1, "verses": [{"number": 1, "text": "In the beginning"}],'
        ' "footnotes": [{"verse_number": 1, "text": "a footnote"}]}'
    )
    chapter = CanonicalChapter.model_validate_json(raw)
    assert chapter.footnotes[0].note_type is None
    assert chapter.footnotes[0].cross_refs == []


# ---- notes enrichment: typed, anchored, cross-referenced -------------------


def test_typed_anchored_note_with_cross_refs_round_trips() -> None:
    chapter = CanonicalChapter(
        number=1,
        verses=[CanonicalVerse(number=1, text="In the beginning God created")],
        footnotes=[
            CanonicalFootnote(
                verse_number=1,
                text="tn The Hebrew term...",
                note_type="tn",
                char_offset=13,
                marker=1,
                ordinal=0,
                cross_refs=[
                    CanonicalCrossRef(
                        to_book_order_index=43,
                        to_chapter=1,
                        to_verse_start=1,
                    ),
                    CanonicalCrossRef(
                        to_book_order_index=19,
                        to_chapter=33,
                        to_verse_start=6,
                        to_verse_end=9,
                    ),
                ],
            )
        ],
    )
    dumped = chapter.model_dump_json()
    reloaded = CanonicalChapter.model_validate_json(dumped)
    fn = reloaded.footnotes[0]
    assert fn.note_type == "tn"
    assert fn.char_offset == 13
    assert fn.ordinal == 0
    assert fn.cross_refs[1].to_verse_end == 9


def test_all_note_types_accepted() -> None:
    for note_type in ("tn", "sn", "tc", "map"):
        fn = CanonicalFootnote(verse_number=1, text="x", note_type=note_type)
        assert fn.note_type == note_type


def test_unknown_note_type_rejected() -> None:
    with pytest.raises(ValidationError):
        CanonicalFootnote(verse_number=1, text="x", note_type="xx")


# ---- notes enrichment: validators ------------------------------------------


def test_char_offset_at_verse_length_allowed() -> None:
    # An offset equal to the length (anchor after the last char) is valid.
    chapter = CanonicalChapter(
        number=1,
        verses=[CanonicalVerse(number=1, text="abc")],
        footnotes=[CanonicalFootnote(verse_number=1, text="x", char_offset=3)],
    )
    assert chapter.footnotes[0].char_offset == 3


def test_char_offset_beyond_verse_length_rejected() -> None:
    with pytest.raises(ValidationError, match="beyond verse length"):
        CanonicalChapter(
            number=1,
            verses=[CanonicalVerse(number=1, text="abc")],
            footnotes=[CanonicalFootnote(verse_number=1, text="x", char_offset=4)],
        )


def test_negative_char_offset_rejected() -> None:
    with pytest.raises(ValidationError):
        CanonicalFootnote(verse_number=1, text="x", char_offset=-1)


def test_cross_ref_book_order_index_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        CanonicalCrossRef(to_book_order_index=67, to_chapter=1, to_verse_start=1)


def test_cross_ref_book_order_index_zero_rejected() -> None:
    with pytest.raises(ValidationError):
        CanonicalCrossRef(to_book_order_index=0, to_chapter=1, to_verse_start=1)


def test_cross_ref_end_before_start_rejected() -> None:
    with pytest.raises(ValidationError, match="before to_verse_start"):
        CanonicalCrossRef(
            to_book_order_index=1,
            to_chapter=1,
            to_verse_start=10,
            to_verse_end=5,
        )


def test_cross_ref_end_equal_start_allowed() -> None:
    ref = CanonicalCrossRef(to_book_order_index=1, to_chapter=1, to_verse_start=5, to_verse_end=5)
    assert ref.to_verse_end == 5
