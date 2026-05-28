"""Tests for the NLT parser."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from soap_journal.parsers.nlt import (
    NLT_CODE,
    NltParseError,
    _parse_numbered_line,
    build_canonical_translation,
    main,
    parse_lines,
    parse_nlt_source,
)

_HERE = Path(__file__).parent
REAL_SOURCE = _HERE.parents[2] / "bibles" / "nlt.pdf"


# ---- helpers ----------------------------------------------------------------


def _make_nlt_text(*sections: str, toc: bool = True) -> str:
    """Build NLT-formatted plain text from sections.

    Optionally prepends a fake TOC (book names not followed by chapter
    markers) to exercise TOC discrimination.
    """
    toc_text = (
        "Genesis\nExodus\nLeviticus\nNumbers\nDeuteronomy\n"
        "Psalms\nRevelation\n\n"
        if toc
        else ""
    )
    return toc_text + "\n".join(sections) + "\n"


# ---- _parse_numbered_line ---------------------------------------------------


def test_numbered_line_basic() -> None:
    result = _parse_numbered_line("1In the beginning God created")
    assert result == (1, "In the beginning God created")


def test_numbered_line_quote() -> None:
    result = _parse_numbered_line('6"Now you will see what I will do')
    assert result == (6, '"Now you will see what I will do')


def test_numbered_line_multi_digit() -> None:
    result = _parse_numbered_line("12And the LORD said to Moses")
    assert result == (12, "And the LORD said to Moses")


def test_numbered_line_rejects_ordinal_1st() -> None:
    assert _parse_numbered_line("1st Samuel") is None


def test_numbered_line_rejects_ordinal_2nd() -> None:
    assert _parse_numbered_line("2nd Chronicles") is None


def test_numbered_line_rejects_ordinal_3rd() -> None:
    assert _parse_numbered_line("3rd John") is None


def test_numbered_line_rejects_fraction() -> None:
    assert _parse_numbered_line("1/4 feet wide") is None


def test_numbered_line_rejects_comma_number() -> None:
    assert _parse_numbered_line("7,500 pounds of silver") is None


def test_numbered_line_rejects_space_lowercase() -> None:
    assert _parse_numbered_line("120 years and he had other sons") is None


# ---- parse_lines (synthetic text) -------------------------------------------


def test_basic_inline_parsing() -> None:
    text = _make_nlt_text(
        "Genesis",
        "1In the beginning God created the heavens and the earth.",
        "2The earth was formless and empty.",
    )
    books, _ = parse_lines(text)
    assert "Genesis" in books
    assert len(books["Genesis"][1]) == 2
    assert books["Genesis"][1][0] == (
        1,
        "In the beginning God created the heavens and the earth.",
    )
    assert books["Genesis"][1][1] == (
        2,
        "The earth was formless and empty.",
    )


def test_chapter_transition_via_sequence_break() -> None:
    """After verse 3, number 2 can't be verse 4 — it starts chapter 2."""
    text = _make_nlt_text(
        "Genesis",
        "1In the beginning God created the heavens.",
        "2The earth was formless.",
        "3Then God said let there be light.",
        "2So the creation of the heavens was completed.",
        "2On the seventh day God rested.",
    )
    books, _ = parse_lines(text)
    assert sorted(books["Genesis"].keys()) == [1, 2]
    assert len(books["Genesis"][1]) == 3
    assert books["Genesis"][2][0] == (
        1,
        "So the creation of the heavens was completed.",
    )
    assert books["Genesis"][2][1] == (2, "On the seventh day God rested.")


def test_psalms_parsing() -> None:
    text = _make_nlt_text(
        "Psalms",
        "PSALM 1",
        "1Oh the joys of those who do not follow the wicked.",
        "2But they delight in the law of the LORD.",
        "PSALM 2",
        "1Why do the nations conspire?",
    )
    books, _ = parse_lines(text)
    assert "Psalms" in books
    assert sorted(books["Psalms"].keys()) == [1, 2]
    assert len(books["Psalms"][1]) == 2
    assert books["Psalms"][1][0] == (
        1,
        "Oh the joys of those who do not follow the wicked.",
    )
    assert len(books["Psalms"][2]) == 1


def test_toc_discrimination() -> None:
    text = (
        "Genesis\nExodus\nLeviticus\n\n"
        "Genesis\n"
        "1In the beginning God created the heavens.\n"
    )
    books, _ = parse_lines(text)
    assert "Genesis" in books
    assert len(books) == 1


def test_ordinal_book_name_resolution() -> None:
    text = _make_nlt_text(
        "1st Samuel",
        "1Now there was a certain man from Ramathaim.",
        toc=False,
    )
    books, renames = parse_lines(text)
    assert "1 Samuel" in books
    assert books["1 Samuel"][1][0] == (
        1,
        "Now there was a certain man from Ramathaim.",
    )
    assert any("1st Samuel" in r for r in renames)


def test_watermark_filtering() -> None:
    text = _make_nlt_text(
        "Genesis",
        "1In the beginning God created.",
        "Search Biiible",
        "2The earth was formless.",
        "Search Biiible.com",
    )
    books, _ = parse_lines(text)
    for _, chapter_verses in books["Genesis"].items():
        for _, verse_text in chapter_verses:
            assert "Search Biiible" not in verse_text


def test_multiline_verse_text() -> None:
    text = _make_nlt_text(
        "Genesis",
        "1In the beginning God created the",
        "heavens and the earth.",
    )
    books, _ = parse_lines(text)
    assert books["Genesis"][1][0] == (
        1,
        "In the beginning God created the heavens and the earth.",
    )


def test_book_transition() -> None:
    text = _make_nlt_text(
        "Genesis",
        "1In the beginning.",
        "Exodus",
        "1These are the names of the sons of Israel.",
    )
    books, _ = parse_lines(text)
    assert "Genesis" in books
    assert "Exodus" in books


def test_quote_style_verse_marker() -> None:
    """Verse text starting with an opening quote is parsed correctly."""
    text = _make_nlt_text(
        "Exodus",
        '1Now these are the names.',
        '2"Now you will see what I will do to Pharaoh.',
    )
    books, _ = parse_lines(text)
    assert "Exodus" in books
    assert books["Exodus"][1][1] == (2, '"Now you will see what I will do to Pharaoh.')


def test_formfeed_in_verse() -> None:
    text = (
        "Genesis\n"
        "1In the beginning God\f"
        "created the heavens and the earth.\n"
    )
    books, _ = parse_lines(text)
    assert books["Genesis"][1][0] == (
        1,
        "In the beginning God created the heavens and the earth.",
    )


def test_continuation_text_with_standalone_number() -> None:
    """Standalone integers (census data) are continuation text, not markers."""
    text = _make_nlt_text(
        "Ezra",
        "1The descendants of Jeshua and Kadmiel . . .",
        "74",
        "2The singers of the family of Asaph . . .",
    )
    books, _ = parse_lines(text)
    # "74" should be appended to verse 1 as continuation text.
    assert "74" in books["Ezra"][1][0][1]


def test_empty_input_raises() -> None:
    with pytest.raises(NltParseError, match="no verse lines found"):
        parse_lines("")


# ---- build_canonical_translation --------------------------------------------


def test_build_rejects_missing_book() -> None:
    books_data = {"Genesis": {1: [(1, "In the beginning.")]}}
    with pytest.raises(NltParseError, match="missing book"):
        build_canonical_translation(books_data)


# ---- CLI tests --------------------------------------------------------------


def test_cli_returns_error_on_missing_file(tmp_path: Path) -> None:
    result = main(
        [str(tmp_path / "nope.pdf"), "--out", str(tmp_path / "out.json")]
    )
    assert result == 2


def test_cli_returns_error_on_pdftotext_not_found(tmp_path: Path) -> None:
    with patch(
        "soap_journal.parsers.nlt._read_pdf",
        side_effect=FileNotFoundError("pdftotext"),
    ):
        result = main(
            [str(tmp_path / "fake.pdf"), "--out", str(tmp_path / "out.json")]
        )
    assert result == 2


def test_cli_returns_error_on_partial_source(tmp_path: Path) -> None:
    partial_text = "Genesis\n1In the beginning.\n"
    with patch("soap_journal.parsers.nlt._read_pdf", return_value=partial_text):
        result = main(
            [str(tmp_path / "fake.pdf"), "--out", str(tmp_path / "out.json")]
        )
    assert result == 1


# ---- full-source integration tests ------------------------------------------


@pytest.mark.skipif(not REAL_SOURCE.exists(), reason="NLT PDF not provided")
class TestRealNltSource:
    """Integration tests against the user's NLT PDF."""

    @pytest.fixture(scope="class")
    def translation(self) -> tuple:
        from soap_journal.parsers.nlt import _read_pdf

        text = _read_pdf(REAL_SOURCE)
        t, warnings = parse_nlt_source(text)
        return t, warnings

    def test_66_books(self, translation: tuple) -> None:
        t, _ = translation
        assert len(t.books) == 66

    def test_1189_chapters(self, translation: tuple) -> None:
        t, _ = translation
        chapters = sum(len(b.chapters) for b in t.books)
        assert chapters == 1189

    def test_verse_count_in_range(self, translation: tuple) -> None:
        t, _ = translation
        verses = sum(
            len(c.verses) for b in t.books for c in b.chapters
        )
        assert 30900 <= verses <= 31200

    def _get_verse(
        self, translation: tuple, book: str, ch: int, v: int
    ) -> str:
        t, _ = translation
        for b in t.books:
            if b.name == book:
                for c in b.chapters:
                    if c.number == ch:
                        for vv in c.verses:
                            if vv.number == v:
                                return vv.text
        raise AssertionError(f"{book} {ch}:{v} not found")

    def test_spot_check_gen_1_1(self, translation: tuple) -> None:
        text = self._get_verse(translation, "Genesis", 1, 1)
        assert "In the beginning" in text
        assert "God created" in text

    def test_spot_check_john_3_16(self, translation: tuple) -> None:
        text = self._get_verse(translation, "John", 3, 16)
        assert "loved the world" in text.lower()

    def test_spot_check_psalm_23_1(self, translation: tuple) -> None:
        text = self._get_verse(translation, "Psalms", 23, 1)
        assert "shepherd" in text.lower()

    def test_spot_check_matt_5_3(self, translation: tuple) -> None:
        text = self._get_verse(translation, "Matthew", 5, 3)
        assert "bless" in text.lower()

    def test_spot_check_rev_22_21(self, translation: tuple) -> None:
        text = self._get_verse(translation, "Revelation", 22, 21)
        assert "grace" in text.lower()

    def test_all_150_psalms(self, translation: tuple) -> None:
        t, _ = translation
        psalms = next(b for b in t.books if b.name == "Psalms")
        assert len(psalms.chapters) == 150

    def test_ordinal_books_resolved(self, translation: tuple) -> None:
        t, _ = translation
        book_names = {b.name for b in t.books}
        ordinal_books = [
            "1 Samuel",
            "2 Samuel",
            "1 Kings",
            "2 Kings",
            "1 Chronicles",
            "2 Chronicles",
            "1 Corinthians",
            "2 Corinthians",
            "1 Thessalonians",
            "2 Thessalonians",
            "1 Timothy",
            "2 Timothy",
            "1 Peter",
            "2 Peter",
            "1 John",
            "2 John",
            "3 John",
        ]
        for name in ordinal_books:
            assert name in book_names, f"{name} not found in parsed books"

    def test_no_headings(self, translation: tuple) -> None:
        t, _ = translation
        total = sum(
            len(c.headings) for b in t.books for c in b.chapters
        )
        assert total == 0

    def test_no_footnotes(self, translation: tuple) -> None:
        t, _ = translation
        total = sum(
            len(c.footnotes) for b in t.books for c in b.chapters
        )
        assert total == 0

    def test_cli_writes_json(self, translation: tuple, tmp_path: Path) -> None:
        t, _ = translation
        out = tmp_path / "nlt.json"
        from soap_journal.parsers.nlt import _write_canonical_json

        _write_canonical_json(t, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["code"] == "NLT"
        assert len(data["books"]) == 66
