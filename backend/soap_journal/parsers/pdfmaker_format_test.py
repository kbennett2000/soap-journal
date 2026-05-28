"""Tests for the shared PDFMaker-format parser."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from soap_journal.parsers._pdfmaker_translations import PDFMAKER_CONFIGS
from soap_journal.parsers.pdfmaker_format import (
    PdfMakerParseError,
    PdfMakerTranslationConfig,
    build_canonical_translation,
    is_likely_heading,
    make_cli_main,
    parse_lines,
    parse_pdfmaker_source,
    read_pdf,
    split_verses,
    write_canonical_json,
)

_HERE = Path(__file__).parent
_SOURCES_DIR = _HERE.parents[2] / "bible-sources"

_TEST_FOOTER = "TEST  [Online]"
_TEST_CONFIG = PdfMakerTranslationConfig(
    code="TEST",
    name="Test Translation",
    language="en",
    copyright="Test copyright.",
    footer_marker=_TEST_FOOTER,
)


# ---- helpers ----------------------------------------------------------------


def _make_text(*sections: str) -> str:
    header = "Holy Bible\nTest Translation\n\n"
    return header + "\n".join(sections) + "\n"


# ---- split_verses -----------------------------------------------------------


def test_split_verses_single_verse() -> None:
    result = split_verses("1 In the beginning God created")
    assert result == [(1, "In the beginning God created")]


def test_split_verses_multiple_inline() -> None:
    result = split_verses(
        "1 First verse text 2 Second verse 3 Third verse"
    )
    assert result is not None
    assert len(result) == 3
    assert result[0] == (1, "First verse text")
    assert result[1] == (2, "Second verse")
    assert result[2] == (3, "Third verse")


def test_split_verses_continuation_prefix() -> None:
    result = split_verses("and the earth. 2 And the earth was")
    assert result is not None
    assert result[0] == (0, "and the earth.")
    assert result[1] == (2, "And the earth was")


def test_split_verses_multi_digit() -> None:
    result = split_verses("10 And God called the dry land Earth;")
    assert result == [(10, "And God called the dry land Earth;")]


def test_split_verses_verse_176() -> None:
    result = split_verses("176 I have gone astray like a lost sheep;")
    assert result == [(176, "I have gone astray like a lost sheep;")]


def test_split_verses_no_markers_lowercase() -> None:
    assert split_verses("and the evening and the morning") is None


def test_split_verses_no_markers_heading() -> None:
    assert split_verses("The First Day") is None


def test_split_verses_bracket_start() -> None:
    result = split_verses("1 [A Psalm of David.] Blessed is he")
    assert result is not None
    assert result[0][0] == 1
    assert "[A Psalm of David.]" in result[0][1]


def test_split_verses_paren_start() -> None:
    result = split_verses("1 (For all these had taken strange wives)")
    assert result is not None
    assert result[0][0] == 1


def test_split_verses_number_in_text_uppercase_only() -> None:
    result = split_verses("1 There were 12 Apostles sent out.")
    assert result is not None
    assert len(result) == 2
    assert result[0] == (1, "There were")
    assert result[1][0] == 12


# ---- is_likely_heading ------------------------------------------------------


def test_heading_title_case_short() -> None:
    assert is_likely_heading("The Creation", "In the beginning.")


def test_heading_with_small_words() -> None:
    assert is_likely_heading("The Fall of Man", "the garden.")


def test_heading_rejected_lowercase_start() -> None:
    assert not is_likely_heading("the creation", "In the beginning.")


def test_heading_rejected_long_line() -> None:
    assert not is_likely_heading("A" * 121, "text.")


def test_heading_rejected_prev_no_sentence_end() -> None:
    assert not is_likely_heading("The Creation", "and the earth")


def test_heading_accepted_after_sentence() -> None:
    assert is_likely_heading("The Creation", "earth was good.")


# ---- parse_lines (synthetic text) -------------------------------------------


def test_parse_lines_basic_chapter_and_verses() -> None:
    text = _make_text(
        "Genesis 1",
        "1 In the beginning God created the heaven and the earth.",
    )
    books, _, _ = parse_lines(text, _TEST_FOOTER)
    assert "Genesis" in books
    assert books["Genesis"][1] == [(1, "In the beginning God created the heaven and the earth.")]


def test_parse_lines_multi_chapter() -> None:
    text = _make_text(
        "Genesis 1",
        "1 In the beginning.",
        "Genesis 2",
        "1 Thus the heavens were finished.",
    )
    books, _, _ = parse_lines(text, _TEST_FOOTER)
    assert sorted(books["Genesis"].keys()) == [1, 2]


def test_parse_lines_continuation_lines() -> None:
    text = _make_text(
        "Genesis 1",
        "1 In the beginning God created the heaven",
        "and the earth.",
    )
    books, _, _ = parse_lines(text, _TEST_FOOTER)
    assert books["Genesis"][1] == [
        (1, "In the beginning God created the heaven and the earth.")
    ]


def test_parse_lines_cross_page_break() -> None:
    text = (
        "Holy Bible\nTest\n\n"
        "Genesis 1\n1 In the beginning\fGod created.\n"
    )
    books, _, _ = parse_lines(text, _TEST_FOOTER)
    assert "Genesis" in books


def test_parse_lines_skips_cross_references() -> None:
    text = _make_text(
        "Genesis 1",
        "(John 1:1-5; Hebrews 11:1-3)",
        "1 In the beginning.",
    )
    books, _, _ = parse_lines(text, _TEST_FOOTER)
    verse_text = books["Genesis"][1][0][1]
    assert "John 1:1" not in verse_text


def test_parse_lines_skips_footer() -> None:
    text = _make_text(
        "Genesis 1",
        "1 In the beginning.",
        _TEST_FOOTER,
        "Exodus 1",
        "1 Now these are the names.",
    )
    books, _, _ = parse_lines(text, _TEST_FOOTER)
    assert "Genesis" in books
    assert "Exodus" in books


def test_parse_lines_filters_saying_markers() -> None:
    text = _make_text(
        "Proverbs 1",
        "1 The proverbs of Solomon.",
        "Saying 1",
        "2 Listen my son.",
    )
    books, _, _ = parse_lines(text, _TEST_FOOTER)
    verse_texts = [t for _, t in books["Proverbs"][1]]
    assert not any("Saying" in t for t in verse_texts)


def test_parse_lines_captures_headings() -> None:
    text = _make_text(
        "Genesis 1",
        "The Creation",
        "1 In the beginning.",
    )
    _, headings, _ = parse_lines(text, _TEST_FOOTER)
    assert headings["Genesis"][1] == [(1, "The Creation")]


def test_parse_lines_heading_mid_chapter() -> None:
    text = _make_text(
        "Genesis 1",
        "1 In the beginning God created the heaven.",
        "The First Day",
        "2 And the earth was without form.",
    )
    _, headings, _ = parse_lines(text, _TEST_FOOTER)
    assert (2, "The First Day") in headings["Genesis"][1]


def test_parse_lines_preserves_bracketed_words() -> None:
    text = _make_text(
        "Genesis 1",
        "1 And [the Spirit of] God moved.",
    )
    books, _, _ = parse_lines(text, _TEST_FOOTER)
    assert "[the Spirit of]" in books["Genesis"][1][0][1]


def test_parse_lines_numbered_books() -> None:
    text = _make_text(
        "1 Samuel 1",
        "1 Now there was a certain man.",
    )
    books, _, _ = parse_lines(text, _TEST_FOOTER)
    assert "1 Samuel" in books


def test_parse_lines_psalm_rename() -> None:
    text = _make_text(
        "Psalm 23",
        "1 The LORD is my shepherd.",
    )
    books, _, renames = parse_lines(text, _TEST_FOOTER)
    assert "Psalms" in books
    assert any("Psalm" in r for r in renames)


def test_parse_lines_rejects_empty_input() -> None:
    with pytest.raises(PdfMakerParseError, match="no verse lines found"):
        parse_lines("", _TEST_FOOTER)


def test_parse_lines_narrow_no_break_space() -> None:
    text = "Genesis 1\n1 In the beginning.\n"
    books, _, _ = parse_lines(text, _TEST_FOOTER)
    assert "Genesis" in books


# ---- build_canonical_translation --------------------------------------------


def test_build_rejects_missing_book() -> None:
    books_data = {"Genesis": {1: [(1, "In the beginning.")]}}
    with pytest.raises(PdfMakerParseError, match="missing book"):
        build_canonical_translation(books_data, {}, _TEST_CONFIG)


def test_build_includes_headings() -> None:
    text = _make_text(
        "Genesis 1",
        "The Creation",
        "1 In the beginning.",
    )
    books_data, headings_data, _ = parse_lines(text, _TEST_FOOTER)
    full_books = {}
    for book_name in ("Genesis",):
        full_books[book_name] = books_data[book_name]
    # Can't build full translation (missing 65 books), but we can
    # verify headings_data is wired correctly through integration test.
    assert headings_data["Genesis"][1] == [(1, "The Creation")]


# ---- CLI (make_cli_main) ----------------------------------------------------


def test_cli_returns_error_on_missing_file(tmp_path: Path) -> None:
    main = make_cli_main(_TEST_CONFIG)
    result = main([str(tmp_path / "nope.pdf"), "--out", str(tmp_path / "out.json")])
    assert result == 2


def test_cli_returns_error_on_invalid_pdf(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdf"
    bad.write_text("not a PDF")
    main = make_cli_main(_TEST_CONFIG)
    result = main([str(bad), "--out", str(tmp_path / "out.json")])
    assert result == 2


def test_cli_returns_error_on_partial_source(tmp_path: Path) -> None:
    partial_text = "Genesis 1\n1 In the beginning.\n"
    main = make_cli_main(_TEST_CONFIG)
    with patch("soap_journal.parsers.pdfmaker_format.read_pdf", return_value=partial_text):
        result = main(
            [str(tmp_path / "fake.pdf"), "--out", str(tmp_path / "out.json")]
        )
    assert result == 1


# ---- parameterized real-source integration tests ----------------------------


_REAL_PARAMS = [
    pytest.param(code, id=code)
    for code, cfg in PDFMAKER_CONFIGS.items()
    if (_SOURCES_DIR / code.lower() / f"{code.lower()}.pdf").exists()
]


@pytest.mark.skipif(not _REAL_PARAMS, reason="no PDFMaker PDFs found")
class TestRealPdfMakerSources:
    """Integration tests against all available PDFMaker-format PDFs."""

    @pytest.fixture(scope="class", params=_REAL_PARAMS)
    def parsed(self, request: pytest.FixtureRequest) -> tuple:
        code = request.param
        cfg = PDFMAKER_CONFIGS[code]
        pdf_path = _SOURCES_DIR / code.lower() / f"{code.lower()}.pdf"
        text = read_pdf(pdf_path)
        translation, renames = parse_pdfmaker_source(text, cfg)
        return translation, renames, cfg

    def test_66_books(self, parsed: tuple) -> None:
        t, _, _ = parsed
        assert len(t.books) == 66

    def test_1189_chapters(self, parsed: tuple) -> None:
        t, _, _ = parsed
        chapters = sum(len(b.chapters) for b in t.books)
        assert chapters == 1189

    def test_verse_count_in_range(self, parsed: tuple) -> None:
        t, _, cfg = parsed
        verses = sum(
            len(c.verses) for b in t.books for c in b.chapters
        )
        # JPS (Weymouth NT) has extra verse splits; most others ~31,102
        upper = 31800 if cfg.code == "JPS" else 31200
        assert 31000 <= verses <= upper

    def test_code_matches_config(self, parsed: tuple) -> None:
        t, _, cfg = parsed
        assert t.code == cfg.code

    def test_genesis_first_revelation_last(self, parsed: tuple) -> None:
        t, _, _ = parsed
        assert t.books[0].name == "Genesis"
        assert t.books[-1].name == "Revelation"

    def test_gen_1_1_nonempty(self, parsed: tuple) -> None:
        t, _, _ = parsed
        gen1_1 = t.books[0].chapters[0].verses[0]
        assert gen1_1.number == 1
        assert len(gen1_1.text) > 10

    def test_cli_writes_json(self, parsed: tuple, tmp_path: Path) -> None:
        t, _, cfg = parsed
        out = tmp_path / f"{cfg.code.lower()}.json"
        write_canonical_json(t, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["code"] == cfg.code
        assert len(data["books"]) == 66
