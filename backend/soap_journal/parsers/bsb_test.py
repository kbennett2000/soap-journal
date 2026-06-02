"""Tests for the BSB parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from soap_journal.parsers.bsb import (
    BSB_CODE,
    BSB_COPYRIGHT,
    BSB_LANGUAGE,
    BSB_NAME,
    OMITTED_VERSE_PLACEHOLDER,
    BsbParseError,
    build_canonical_translation,
    main,
    parse_bsb_source,
    parse_lines,
)

_HERE = Path(__file__).parent
MINI_FIXTURE = _HERE / "_test_data" / "bsb_mini.txt"

# _HERE is <repo>/backend/soap_journal/parsers; parents[2] is <repo>.
REAL_SOURCE = _HERE.parents[2] / "bible-sources" / "bsb" / "bsb.txt"


# ---- line parser (mini fixture) -------------------------------------------


def test_parse_lines_groups_by_book_and_chapter() -> None:
    books_data, renames = parse_lines(MINI_FIXTURE.read_text(encoding="utf-8"))

    # Genesis 1:1, 1:2, 2:1; John 3:16, 3:17; Psalms 23:1.
    # Psalm -> Psalms is a rename, so the canonical key is "Psalms".
    assert set(books_data.keys()) == {"Genesis", "John", "Psalms"}
    assert sorted(books_data["Genesis"].keys()) == [1, 2]
    assert books_data["Genesis"][1] == [
        (1, "In the beginning God created the heavens and the earth."),
        (
            2,
            "Now the earth was formless and void, and darkness was over the surface of the deep.",
        ),
    ]
    assert books_data["Genesis"][2] == [
        (1, "Thus the heavens and the earth were completed in all their vast array.")
    ]
    assert renames == ["Psalm -> Psalms"]


def test_parse_lines_strips_bom() -> None:
    raw = MINI_FIXTURE.read_text(encoding="utf-8")
    assert raw.startswith("﻿")
    # Should still parse without error.
    books_data, _ = parse_lines(raw)
    assert books_data  # not empty


def test_parse_lines_rejects_unknown_book() -> None:
    bad = "Verse\tBerean Standard Bible\nMade Up Book 1:1\tdoes not exist.\n"
    with pytest.raises(BsbParseError, match="does not match any canonical name or alias"):
        parse_lines(bad)


def test_parse_lines_rejects_unparseable_reference() -> None:
    bad = "Verse\tBerean Standard Bible\njunk\tthe text.\n"
    with pytest.raises(BsbParseError, match="no verse lines found"):
        parse_lines(bad)


def test_parse_lines_substitutes_placeholder_for_empty_text() -> None:
    # The real BSB ships 16 verses with empty text (Matt 17:21, Mark 7:16,
    # John 5:4, ...). The parser must keep the slot to preserve 1..N
    # chapter numbering and substitute a recognizable placeholder.
    raw = (
        "Verse\tBerean Standard Bible\n"
        "Genesis 1:1\tIn the beginning.\n"
        "Genesis 1:2\t\n"
        "Genesis 1:3\tAnd God said.\n"
    )
    books_data, _ = parse_lines(raw)
    assert books_data["Genesis"][1] == [
        (1, "In the beginning."),
        (2, OMITTED_VERSE_PLACEHOLDER),
        (3, "And God said."),
    ]


# ---- canonical builder (requires all 66 books) -----------------------------


def test_build_canonical_translation_rejects_missing_book() -> None:
    books_data, _ = parse_lines(MINI_FIXTURE.read_text(encoding="utf-8"))
    with pytest.raises(BsbParseError, match="missing book"):
        build_canonical_translation(books_data)


# ---- CLI smoke test (mini fixture only exercises arg parsing) -------------


def test_cli_returns_error_on_partial_source(tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    rc = main([str(MINI_FIXTURE), "--out", str(out)])
    assert rc == 1
    assert not out.exists()


# ---- full source smoke test ------------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(not REAL_SOURCE.exists(), reason="BSB source not bundled")
def test_parse_real_bsb_source_has_expected_shape() -> None:
    translation, renames = parse_bsb_source(REAL_SOURCE.read_text(encoding="utf-8"))

    assert translation.code == BSB_CODE
    assert translation.name == BSB_NAME
    assert translation.language == BSB_LANGUAGE
    assert translation.copyright == BSB_COPYRIGHT

    # 66 books in canonical order.
    assert len(translation.books) == 66
    assert translation.books[0].name == "Genesis"
    assert translation.books[-1].name == "Revelation"

    # Standard chapter count for a Protestant canon Bible.
    total_chapters = sum(len(b.chapters) for b in translation.books)
    assert total_chapters == 1189

    # Standard verse count for the BSB.
    total_verses = sum(len(c.verses) for b in translation.books for c in b.chapters)
    assert total_verses == 31102

    # Spot checks.
    genesis = next(b for b in translation.books if b.name == "Genesis")
    assert genesis.chapters[0].verses[0].text.startswith("In the beginning")

    revelation = next(b for b in translation.books if b.name == "Revelation")
    assert revelation.chapters[-1].number == 22
    assert revelation.chapters[-1].verses[-1].number == 21

    # Psalm -> Psalms is the expected rename for the BSB source.
    assert renames == ["Psalm -> Psalms"]


@pytest.mark.slow
@pytest.mark.skipif(not REAL_SOURCE.exists(), reason="BSB source not bundled")
def test_cli_writes_canonical_json_for_real_source(tmp_path: Path) -> None:
    out = tmp_path / "bsb.json"
    rc = main([str(REAL_SOURCE), "--out", str(out)])
    assert rc == 0
    assert out.exists()

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["code"] == BSB_CODE
    assert len(data["books"]) == 66
