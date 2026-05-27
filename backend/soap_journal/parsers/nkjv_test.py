"""Tests for the NKJV parser."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from soap_journal.parsers.nkjv import (
    NKJV_CODE,
    NKJV_COPYRIGHT,
    NKJV_LANGUAGE,
    NKJV_NAME,
    NkjvParseError,
    build_canonical_translation,
    main,
    parse_lines,
    parse_nkjv_source,
)

_HERE = Path(__file__).parent
REAL_SOURCE = _HERE.parents[2] / "bibles" / "nkjv.pdf"


# ---- helpers ----------------------------------------------------------------


def _make_nkjv_text(*verse_lines: str, title: bool = True) -> str:
    """Build NKJV-formatted plain text from verse lines.

    Each verse_line should be like "Gen 1:1 In the beginning...".
    Continuation lines (no verse prefix) can follow naturally.
    """
    header = "The Holy Bible\nNew King James Version 1982 NKJV\n" if title else ""
    return header + "\n".join(verse_lines) + "\n"


# ---- line parser (plain text, no PDF needed) --------------------------------


def test_parse_lines_groups_by_book_and_chapter() -> None:
    text = _make_nkjv_text(
        "Gen 1:1 In the start the heavens and the land were formed.",
        "Gen 1:2 The land was empty and void.",
        "Gen 2:1 The heavens and the land were finished.",
        "Joh 3:16 For the Creator so loved the world.",
        "Joh 3:17 The Creator did not send His Son to condemn.",
        "Psa 23:1 The LORD is my shepherd I lack nothing.",
    )
    books_data, renames = parse_lines(text)

    assert set(books_data.keys()) == {"Genesis", "John", "Psalms"}
    assert sorted(books_data["Genesis"].keys()) == [1, 2]
    assert books_data["Genesis"][1] == [
        (1, "In the start the heavens and the land were formed."),
        (2, "The land was empty and void."),
    ]
    assert books_data["Genesis"][2] == [
        (1, "The heavens and the land were finished."),
    ]
    assert books_data["John"][3] == [
        (16, "For the Creator so loved the world."),
        (17, "The Creator did not send His Son to condemn."),
    ]
    assert books_data["Psalms"][23] == [
        (1, "The LORD is my shepherd I lack nothing."),
    ]


def test_parse_lines_joins_continuation_lines() -> None:
    text = _make_nkjv_text(
        "Gen 1:2 Now the earth was formless and void, and darkness was",
        "over the surface of the deep. And the Spirit of God was hovering",
        "over the face of the waters.",
    )
    books_data, _ = parse_lines(text)
    assert books_data["Genesis"][1] == [
        (
            2,
            "Now the earth was formless and void, and darkness was "
            "over the surface of the deep. And the Spirit of God was hovering "
            "over the face of the waters.",
        ),
    ]


def test_parse_lines_joins_across_page_break() -> None:
    text = _make_nkjv_text(
        "Gen 1:2 Now the earth was formless and void,\f"
        "and darkness was over the surface of the deep.",
    )
    books_data, _ = parse_lines(text)
    assert books_data["Genesis"][1] == [
        (2, "Now the earth was formless and void, and darkness was over the surface of the deep."),
    ]


def test_parse_lines_multiple_continuation_lines() -> None:
    text = _make_nkjv_text(
        "Gen 1:1 Line one of a very",
        "long verse that spans",
        "three lines in the",
        "source PDF output.",
    )
    books_data, _ = parse_lines(text)
    assert books_data["Genesis"][1] == [
        (1, "Line one of a very long verse that spans three lines in the source PDF output."),
    ]


def test_parse_lines_skips_title_lines() -> None:
    text = (
        "The Holy Bible\nNew King James Version 1982 NKJV\nGen 1:1 In the beginning God created.\n"
    )
    books_data, _ = parse_lines(text)
    assert "Genesis" in books_data
    assert books_data["Genesis"][1] == [(1, "In the beginning God created.")]


def test_parse_lines_preserves_bracketed_italics() -> None:
    text = _make_nkjv_text(
        "Gen 1:1 And He [was] the one who [had given] them life.",
    )
    books_data, _ = parse_lines(text)
    assert books_data["Genesis"][1] == [
        (1, "And He [was] the one who [had given] them life."),
    ]


def test_parse_lines_rejects_unknown_abbreviation() -> None:
    text = _make_nkjv_text("XYZ 1:1 Some text here.")
    with pytest.raises(NkjvParseError, match="does not match any canonical name or alias"):
        parse_lines(text)


def test_parse_lines_empty_input() -> None:
    with pytest.raises(NkjvParseError, match="no verse lines found"):
        parse_lines("")


def test_parse_lines_no_verses() -> None:
    text = "The Holy Bible\nNew King James Version 1982 NKJV\n"
    with pytest.raises(NkjvParseError, match="no verse lines found"):
        parse_lines(text)


def test_parse_lines_records_rename_notices() -> None:
    # "Psa" resolves to canonical "Psalms", which differs from the abbreviation.
    text = _make_nkjv_text("Psa 23:1 The LORD is my shepherd.")
    _, renames = parse_lines(text)
    assert renames == ["Psa -> Psalms"]


def test_parse_lines_handles_numbered_book_abbreviations() -> None:
    text = _make_nkjv_text(
        "1Sa 1:1 There was a certain man.",
        "2Ki 1:1 After the death of the king.",
        "3Jo 1:1 The Elder, to the beloved.",
    )
    books_data, _ = parse_lines(text)
    assert "1 Samuel" in books_data
    assert "2 Kings" in books_data
    assert "3 John" in books_data


# ---- canonical builder (requires all 66 books) ------------------------------


def test_build_canonical_translation_rejects_missing_book() -> None:
    text = _make_nkjv_text(
        "Gen 1:1 In the beginning.",
        "Joh 3:16 For God so loved.",
    )
    books_data, _ = parse_lines(text)
    with pytest.raises(NkjvParseError, match="missing book"):
        build_canonical_translation(books_data)


# ---- CLI tests ---------------------------------------------------------------


def test_cli_returns_error_on_partial_source(tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    text = _make_nkjv_text(
        "Gen 1:1 In the beginning.",
        "Joh 3:16 For God so loved.",
    )
    with patch("soap_journal.parsers.nkjv._read_pdf", return_value=text):
        rc = main([str(tmp_path / "fake.pdf"), "--out", str(out)])
    assert rc == 1
    assert not out.exists()


def test_cli_returns_error_on_missing_file(tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    rc = main([str(tmp_path / "nonexistent.pdf"), "--out", str(out)])
    assert rc == 2
    assert not out.exists()


def test_cli_returns_error_on_invalid_pdf(tmp_path: Path) -> None:
    bad_pdf = tmp_path / "not_a_pdf.pdf"
    bad_pdf.write_text("This is not a PDF file.", encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main([str(bad_pdf), "--out", str(out)])
    assert rc == 2
    assert not out.exists()


# ---- PDF reading (integration) -----------------------------------------------


def test_read_pdf_with_generated_fixture(tmp_path: Path) -> None:
    """Generate a small PDF with fpdf2, then verify _read_pdf extracts text."""
    from fpdf import FPDF

    from soap_journal.parsers.nkjv import _read_pdf

    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.cell(text="The Holy Bible")
    pdf.ln()
    pdf.cell(text="New King James Version 1982 NKJV")
    pdf.ln()
    pdf.cell(text="Gen 1:1 In the beginning God created the heavens and the earth.")
    pdf.ln()
    pdf.cell(text="Gen 1:2 The earth was without form and void.")

    pdf.add_page()
    pdf.cell(text="Joh 3:16 For God so loved the world that He gave.")

    pdf_path = tmp_path / "test.pdf"
    pdf.output(str(pdf_path))

    extracted = _read_pdf(pdf_path)
    assert "Gen 1:1" in extracted
    assert "Gen 1:2" in extracted
    assert "Joh 3:16" in extracted


def test_end_to_end_pdf_parse(tmp_path: Path) -> None:
    """Generate a mini PDF, run parse_lines on extracted text."""
    from fpdf import FPDF

    from soap_journal.parsers.nkjv import _read_pdf

    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.cell(text="The Holy Bible")
    pdf.ln()
    pdf.cell(text="New King James Version 1982 NKJV")
    pdf.ln()
    pdf.cell(text="Gen 1:1 In the beginning God created the heavens.")
    pdf.ln()
    pdf.cell(text="Gen 1:2 The earth was without form.")

    pdf_path = tmp_path / "mini.pdf"
    pdf.output(str(pdf_path))

    extracted = _read_pdf(pdf_path)
    books_data, _ = parse_lines(extracted)
    assert "Genesis" in books_data
    assert 1 in books_data["Genesis"]
    assert len(books_data["Genesis"][1]) == 2


# ---- full source tests (skipped in CI) ---------------------------------------


@pytest.mark.skipif(not REAL_SOURCE.exists(), reason="NKJV PDF not provided")
def test_parse_real_nkjv_source_has_expected_shape() -> None:
    from soap_journal.parsers.nkjv import _read_pdf

    source_text = _read_pdf(REAL_SOURCE)
    translation, renames = parse_nkjv_source(source_text)

    assert translation.code == NKJV_CODE
    assert translation.name == NKJV_NAME
    assert translation.language == NKJV_LANGUAGE
    assert translation.copyright == NKJV_COPYRIGHT

    assert len(translation.books) == 66
    assert translation.books[0].name == "Genesis"
    assert translation.books[-1].name == "Revelation"

    total_chapters = sum(len(b.chapters) for b in translation.books)
    assert total_chapters == 1189

    total_verses = sum(len(c.verses) for b in translation.books for c in b.chapters)
    assert total_verses == 31102

    genesis = next(b for b in translation.books if b.name == "Genesis")
    assert genesis.chapters[0].verses[0].text.startswith("In the beginning")

    revelation = next(b for b in translation.books if b.name == "Revelation")
    assert revelation.chapters[-1].number == 22
    assert revelation.chapters[-1].verses[-1].number == 21


@pytest.mark.skipif(not REAL_SOURCE.exists(), reason="NKJV PDF not provided")
def test_cli_writes_canonical_json_for_real_source(tmp_path: Path) -> None:
    out = tmp_path / "nkjv.json"
    rc = main([str(REAL_SOURCE), "--out", str(out)])
    assert rc == 0
    assert out.exists()

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["code"] == NKJV_CODE
    assert len(data["books"]) == 66
