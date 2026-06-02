"""Tests for the ESV parser."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from soap_journal.parsers.esv import (
    ESV_CODE,
    EsvParseError,
    _extract_footnote,
    build_canonical_translation,
    main,
    parse_lines,
    parse_esv_source,
)

_HERE = Path(__file__).parent
REAL_SOURCE = _HERE.parents[2] / "bibles" / "esv.pdf"


# ---- helpers ----------------------------------------------------------------


def _make_esv_text(*sections: str) -> str:
    toc = "1. Genesis\n2. Exodus\n66. Revelation\n\n"
    return toc + "\n".join(sections) + "\n"


# ---- footnote extraction ----------------------------------------------------


def test_extract_footnote_or() -> None:
    clean, fn = _extract_footnote("in the landOr earth; also verse 6")
    assert clean == "in the land"
    assert fn == "Or earth; also verse 6"


def test_extract_footnote_hebrew() -> None:
    clean, fn = _extract_footnote("word of GodHebrew Elohim")
    assert clean == "word of God"
    assert fn == "Hebrew Elohim"


def test_extract_footnote_none() -> None:
    clean, fn = _extract_footnote("In the beginning, God created the heavens.")
    assert clean == "In the beginning, God created the heavens."
    assert fn is None


def test_extract_footnote_not_split_on_mid_sentence_or() -> None:
    clean, fn = _extract_footnote("rich or poor, all are welcome.")
    assert fn is None
    assert "rich or poor" in clean


# ---- parse_lines (synthetic text) -------------------------------------------


def test_chapter_header_basic() -> None:
    text = _make_esv_text(
        "1.1. Chapter 1",
        "1 ",
        "In the beginning, God created the heavens.",
    )
    books, _, _, _ = parse_lines(text)
    assert "Genesis" in books
    assert books["Genesis"][1] == [(1, "In the beginning, God created the heavens.")]


def test_chapter_header_with_formfeed() -> None:
    text = "1. Genesis\n\f1.1. Chapter 1\n1 \nIn the beginning.\n"
    books, _, _, _ = parse_lines(text)
    assert "Genesis" in books


def test_toc_skipped() -> None:
    text = _make_esv_text(
        "1.1. Chapter 1",
        "1 ",
        "In the beginning.",
    )
    books, _, _, _ = parse_lines(text)
    assert len(books) == 1
    assert "Genesis" in books


def test_verse_marker_and_text() -> None:
    text = _make_esv_text(
        "1.1. Chapter 1",
        "1 ",
        "First verse text.",
        "2 ",
        "Second verse text.",
    )
    books, _, _, _ = parse_lines(text)
    assert len(books["Genesis"][1]) == 2
    assert books["Genesis"][1][0] == (1, "First verse text.")
    assert books["Genesis"][1][1] == (2, "Second verse text.")


def test_verse_text_multiline() -> None:
    text = _make_esv_text(
        "1.1. Chapter 1",
        "1 ",
        "First line of verse.",
        "Second line of verse.",
    )
    books, _, _, _ = parse_lines(text)
    assert books["Genesis"][1] == [
        (1, "First line of verse. Second line of verse.")
    ]


def test_standalone_pericope() -> None:
    text = _make_esv_text(
        "1.1. Chapter 1",
        "(The Creation of the World)",
        "1 ",
        "In the beginning.",
    )
    _, headings, _, _ = parse_lines(text)
    assert headings["Genesis"][1] == [(1, "The Creation of the World")]


def test_verse_with_pericope() -> None:
    text = _make_esv_text(
        "1.2. Chapter 2",
        "1 ",
        "First verse.",
        "4(The Creation of Man and Woman)",
        "These are the generations.",
    )
    books, headings, _, _ = parse_lines(text)
    assert (4, "These are the generations.") in books["Genesis"][2]
    assert (4, "The Creation of Man and Woman") in headings["Genesis"][2]


def test_cross_reference_not_captured() -> None:
    text = _make_esv_text(
        "1.1. Chapter 1",
        "(Genesis 22:1-10)",
        "1 ",
        "In the beginning.",
    )
    _, headings, _, _ = parse_lines(text)
    heading_texts = [h[1] for h in headings.get("Genesis", {}).get(1, [])]
    assert "Genesis 22:1-10" not in heading_texts


def test_parenthesized_verse_text_not_heading() -> None:
    text = _make_esv_text(
        "43.1. Chapter 1",
        "24 ",
        "(Now they had been sent from the Pharisees.)",
    )
    books, headings, _, _ = parse_lines(text)
    verse_text = books["John"][1][0][1]
    assert "Pharisees" in verse_text
    heading_texts = [h[1] for h in headings.get("John", {}).get(1, [])]
    assert all("Pharisees" not in h for h in heading_texts)


def test_page_numbers_skipped() -> None:
    text = _make_esv_text(
        "1.1. Chapter 1",
        "1 ",
        "First verse.",
        "5432",
        "Second line of first verse.",
    )
    books, _, _, _ = parse_lines(text)
    verse_text = books["Genesis"][1][0][1]
    assert "5432" not in verse_text
    assert "Second line" in verse_text


def test_section_label_fused_with_verse() -> None:
    text = _make_esv_text(
        "19.119. Chapter 119",
        "1 ",
        "Blessed are those.",
        "9Beth",
        "How can a young man.",
    )
    books, headings, _, _ = parse_lines(text)
    assert (9, "How can a young man.") in books["Psalms"][119]
    assert (9, "Beth") in headings["Psalms"][119]


def test_multi_chapter_multi_book() -> None:
    text = _make_esv_text(
        "1.1. Chapter 1",
        "1 ",
        "Genesis 1:1 text.",
        "1.2. Chapter 2",
        "1 ",
        "Genesis 2:1 text.",
        "2.1. Chapter 1",
        "1 ",
        "Exodus 1:1 text.",
    )
    books, _, _, _ = parse_lines(text)
    assert "Genesis" in books
    assert "Exodus" in books
    assert sorted(books["Genesis"].keys()) == [1, 2]


def test_empty_input_raises() -> None:
    with pytest.raises(EsvParseError, match="no verse lines found"):
        parse_lines("")


def test_build_rejects_missing_book() -> None:
    books_data = {"Genesis": {1: [(1, "In the beginning.")]}}
    with pytest.raises(EsvParseError, match="missing book"):
        build_canonical_translation(books_data, {}, {})


# ---- CLI tests --------------------------------------------------------------


def test_cli_returns_error_on_missing_file(tmp_path: Path) -> None:
    result = main([str(tmp_path / "nope.pdf"), "--out", str(tmp_path / "out.json")])
    assert result == 2


def test_cli_returns_error_on_invalid_pdf(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdf"
    bad.write_text("not a PDF")
    result = main([str(bad), "--out", str(tmp_path / "out.json")])
    assert result == 2


def test_cli_returns_error_on_partial_source(tmp_path: Path) -> None:
    partial_text = "1.1. Chapter 1\n1 \nIn the beginning.\n"
    with patch("soap_journal.parsers.esv._read_pdf", return_value=partial_text):
        result = main(
            [str(tmp_path / "fake.pdf"), "--out", str(tmp_path / "out.json")]
        )
    assert result == 1


# ---- full-source integration tests ------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(not REAL_SOURCE.exists(), reason="ESV PDF not provided")
class TestRealEsvSource:
    """Integration tests against the user's ESV PDF."""

    @pytest.fixture(scope="class")
    def translation(self) -> tuple:
        from soap_journal.parsers.esv import _read_pdf

        text = _read_pdf(REAL_SOURCE)
        t, warnings = parse_esv_source(text)
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
        assert 31000 <= verses <= 31200

    def _get_verse(self, translation: tuple, book: str, ch: int, v: int) -> str:
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
        assert "God so loved the world" in text

    def test_spot_check_psalm_23_1(self, translation: tuple) -> None:
        text = self._get_verse(translation, "Psalms", 23, 1)
        assert "shepherd" in text

    def test_spot_check_rev_22_21(self, translation: tuple) -> None:
        text = self._get_verse(translation, "Revelation", 22, 21)
        assert "grace" in text.lower()

    def test_has_headings(self, translation: tuple) -> None:
        t, _ = translation
        total = sum(
            len(c.headings) for b in t.books for c in b.chapters
        )
        assert total > 500

    def test_has_footnotes(self, translation: tuple) -> None:
        t, _ = translation
        total = sum(
            len(c.footnotes) for b in t.books for c in b.chapters
        )
        assert total > 0

    def test_song_of_solomon_canonical_name(self, translation: tuple) -> None:
        t, _ = translation
        book_names = [b.name for b in t.books]
        assert "Song of Solomon" in book_names

    def test_cli_writes_json(self, translation: tuple, tmp_path: Path) -> None:
        t, _ = translation
        out = tmp_path / "esv.json"
        from soap_journal.parsers.esv import _write_canonical_json

        _write_canonical_json(t, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["code"] == "ESV"
        assert len(data["books"]) == 66
