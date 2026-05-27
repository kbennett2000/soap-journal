"""Tests for the verse reference parser."""

from __future__ import annotations

import pytest

from soap_journal.core.references import (
    ReferenceParseError,
    parse_reference,
    parse_reference_or_raise,
)


# ---- accepted forms --------------------------------------------------------


def test_single_verse() -> None:
    ref = parse_reference("John 3:16")
    assert ref.book.name == "John"
    assert ref.chapter == 3
    assert ref.start_verse == 16
    assert ref.end_verse == 16
    assert ref.canonical_string == "John 3:16"


def test_verse_range() -> None:
    ref = parse_reference("John 3:16-20")
    assert ref.start_verse == 16
    assert ref.end_verse == 20
    assert ref.canonical_string == "John 3:16-20"


def test_whole_chapter() -> None:
    ref = parse_reference("John 3")
    assert ref.chapter == 3
    assert ref.start_verse is None
    assert ref.end_verse is None
    assert ref.canonical_string == "John 3"


def test_abbreviation() -> None:
    ref = parse_reference("Jn 3:16")
    assert ref.book.name == "John"
    assert ref.canonical_string == "John 3:16"


def test_no_space_numbered_book() -> None:
    ref = parse_reference("1John 3:16")
    assert ref.book.name == "1 John"
    assert ref.canonical_string == "1 John 3:16"


def test_spaced_numbered_book_abbreviation() -> None:
    ref = parse_reference("1 Cor 13")
    assert ref.book.name == "1 Corinthians"
    assert ref.canonical_string == "1 Corinthians 13"


def test_alias_song_of_songs() -> None:
    ref = parse_reference("Song of Songs 2:1")
    assert ref.book.name == "Song of Solomon"
    assert ref.canonical_string == "Song of Solomon 2:1"


def test_alias_apocalypse() -> None:
    ref = parse_reference("Apocalypse 22:21")
    assert ref.book.name == "Revelation"
    assert ref.canonical_string == "Revelation 22:21"


def test_lowercase_input_normalizes_to_canonical() -> None:
    ref = parse_reference("john 3:16")
    assert ref.canonical_string == "John 3:16"


def test_uppercase_input_normalizes() -> None:
    ref = parse_reference("JOHN 3:16")
    assert ref.canonical_string == "John 3:16"


def test_whitespace_tolerant() -> None:
    ref = parse_reference("  John   3 : 16 - 20  ")
    assert ref.canonical_string == "John 3:16-20"


def test_en_dash_range() -> None:
    ref = parse_reference("John 3:16–20")
    assert ref.canonical_string == "John 3:16-20"


def test_em_dash_range() -> None:
    ref = parse_reference("John 3:16—20")
    assert ref.canonical_string == "John 3:16-20"


def test_mixed_alias_with_range_normalizes() -> None:
    ref = parse_reference("jn 3:16-20")
    assert ref.canonical_string == "John 3:16-20"


def test_single_verse_range_collapses_to_single_verse() -> None:
    ref = parse_reference("John 3:16-16")
    assert ref.start_verse == 16
    assert ref.end_verse == 16
    assert ref.canonical_string == "John 3:16"


# ---- rejected forms --------------------------------------------------------


def test_empty_input_rejected() -> None:
    with pytest.raises(ReferenceParseError, match="empty"):
        parse_reference("")


def test_whitespace_only_rejected() -> None:
    with pytest.raises(ReferenceParseError, match="empty"):
        parse_reference("   ")


def test_book_only_rejected() -> None:
    with pytest.raises(ReferenceParseError, match="missing a chapter number"):
        parse_reference("John")


def test_unknown_book_rejected() -> None:
    with pytest.raises(ReferenceParseError, match="unknown book"):
        parse_reference("Frodo 3:16")


def test_reversed_range_rejected() -> None:
    with pytest.raises(ReferenceParseError, match="end verse must be >= start verse"):
        parse_reference("John 3:20-16")


def test_chapter_zero_rejected() -> None:
    # "John 0:1" — parser regex requires at least one digit; chapter=0
    # survives the regex and is rejected by the value check.
    with pytest.raises(ReferenceParseError, match="chapter must be 1"):
        parse_reference("John 0:1")


def test_verse_zero_rejected() -> None:
    with pytest.raises(ReferenceParseError, match="verse must be 1"):
        parse_reference("John 3:0")


def test_negative_chapter_rejected() -> None:
    # "-1" isn't matched by the regex (it requires digits); falls through to
    # the generic "could not parse" path.
    with pytest.raises(ReferenceParseError, match="could not parse"):
        parse_reference("John -1:1")


def test_garbage_input_rejected() -> None:
    with pytest.raises(ReferenceParseError, match="could not parse"):
        parse_reference("hello")


def test_chapter_only_no_book_rejected() -> None:
    # "3:16" has no book; book pattern requires alphabetic chars.
    with pytest.raises(ReferenceParseError, match="could not parse"):
        parse_reference("3:16")


def test_colon_with_no_verse_rejected() -> None:
    with pytest.raises(ReferenceParseError, match="could not parse"):
        parse_reference("John :")


def test_multiple_references_rejected_semicolon() -> None:
    with pytest.raises(ReferenceParseError, match="multiple references"):
        parse_reference("John 3:16; Rom 8:28")


def test_multiple_references_rejected_comma() -> None:
    with pytest.raises(ReferenceParseError, match="multiple references"):
        parse_reference("John 3:16, Rom 8:28")


def test_cross_chapter_range_rejected_via_strict_parser() -> None:
    with pytest.raises(
        ReferenceParseError, match="cross-chapter ranges are not supported"
    ):
        parse_reference_or_raise("John 3:30-4:2")


def test_cross_chapter_range_also_rejected_by_base_parser() -> None:
    # Base parse_reference doesn't know about the "cross-chapter not
    # supported" branding but still rejects because the regex won't match.
    with pytest.raises(ReferenceParseError, match="could not parse"):
        parse_reference("John 3:30-4:2")
