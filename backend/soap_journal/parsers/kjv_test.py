"""Tests for the KJV parser."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from soap_journal.parsers.kjv import (
    KJV_CODE,
    KJV_COPYRIGHT,
    KJV_LANGUAGE,
    KJV_NAME,
    KjvParseError,
    _is_likely_heading,
    _split_verses,
    build_canonical_translation,
    main,
    parse_lines,
    parse_kjv_source,
)

_HERE = Path(__file__).parent
REAL_SOURCE = _HERE.parents[2] / "bible-sources" / "kjv" / "kjv.pdf"


# ---- helpers ----------------------------------------------------------------


def _make_kjv_text(*sections: str) -> str:
    """Build KJV-formatted plain text from line groups.

    Each section is one or more lines.  A TOC header is prepended
    so that the parser's "skip until first chapter header" logic
    is exercised.
    """
    header = "Holy Bible\nKing James Version\n\n"
    return header + "\n".join(sections) + "\n"


# ---- _split_verses unit tests -----------------------------------------------


def test_split_verses_single_verse() -> None:
    result = _split_verses("1 In the beginning God created the heaven.")
    assert result == [(1, "In the beginning God created the heaven.")]


def test_split_verses_multiple_inline() -> None:
    result = _split_verses(
        "1 In the beginning God created the heaven. 2 And the earth was void. "
        "3 And God said, Let there be light."
    )
    assert result is not None
    assert len(result) == 3
    assert result[0][0] == 1
    assert result[1][0] == 2
    assert result[2][0] == 3


def test_split_verses_continuation_prefix() -> None:
    result = _split_verses(
        "and darkness was upon the deep. 3 And God said, Let there be light."
    )
    assert result is not None
    assert result[0] == (0, "and darkness was upon the deep.")
    assert result[1] == (3, "And God said, Let there be light.")


def test_split_verses_multi_digit() -> None:
    result = _split_verses("10 And God called the dry land Earth.")
    assert result == [(10, "And God called the dry land Earth.")]


def test_split_verses_verse_176() -> None:
    result = _split_verses("176 I have gone astray like a lost sheep.")
    assert result == [(176, "I have gone astray like a lost sheep.")]


def test_split_verses_no_markers_lowercase() -> None:
    assert _split_verses("and darkness was upon the deep.") is None


def test_split_verses_no_markers_heading() -> None:
    assert _split_verses("The Creation") is None


def test_split_verses_bracket_start() -> None:
    result = _split_verses("1 [A Psalm of David.] The LORD is my shepherd.")
    assert result is not None
    assert result[0] == (1, "[A Psalm of David.] The LORD is my shepherd.")


def test_split_verses_paren_start() -> None:
    result = _split_verses(
        "27 (For all these abominations have the men of the land done.)"
    )
    assert result is not None
    assert result[0][0] == 27
    assert result[0][1].startswith("(For all these")


def test_split_verses_number_in_text() -> None:
    line = "1 And the 12 Tribes of Israel were gathered."
    result = _split_verses(line)
    assert result is not None
    assert result[0][0] == 1


# ---- _is_likely_heading unit tests ------------------------------------------


def test_heading_title_case_short() -> None:
    assert _is_likely_heading("The Creation", "waters.") is True


def test_heading_with_small_words() -> None:
    assert _is_likely_heading("The Sermon on the Mount", "him.") is True


def test_heading_rejected_lowercase_start() -> None:
    assert _is_likely_heading("and darkness was upon the deep.", "void;") is False


def test_heading_rejected_long_line() -> None:
    long = "A" * 130
    assert _is_likely_heading(long, "end.") is False


def test_heading_rejected_prev_no_sentence_end() -> None:
    assert _is_likely_heading("The First Day", "saying,") is False


def test_heading_accepted_after_sentence() -> None:
    assert _is_likely_heading("The First Day", "first day.") is True


# ---- parse_lines (synthetic text, no PDF needed) ----------------------------


def test_parse_lines_basic_chapter_and_verses() -> None:
    text = _make_kjv_text(
        "Genesis 1",
        "1 In the beginning God created the heaven and the earth. "
        "2 And the earth was without form.",
    )
    books, headings, renames = parse_lines(text)
    assert "Genesis" in books
    assert books["Genesis"][1] == [
        (1, "In the beginning God created the heaven and the earth."),
        (2, "And the earth was without form."),
    ]


def test_parse_lines_multi_chapter() -> None:
    text = _make_kjv_text(
        "Genesis 1",
        "1 In the beginning God created the heaven.",
        "Genesis 2",
        "1 Thus the heavens were finished.",
    )
    books, _, _ = parse_lines(text)
    assert sorted(books["Genesis"].keys()) == [1, 2]
    assert books["Genesis"][1] == [
        (1, "In the beginning God created the heaven.")
    ]
    assert books["Genesis"][2] == [
        (1, "Thus the heavens were finished.")
    ]


def test_parse_lines_continuation_lines() -> None:
    text = _make_kjv_text(
        "Genesis 1",
        "2 And the earth was without form, and void;",
        "and darkness [was] upon the face of the deep.",
    )
    books, _, _ = parse_lines(text)
    assert books["Genesis"][1] == [
        (
            2,
            "And the earth was without form, and void; "
            "and darkness [was] upon the face of the deep.",
        )
    ]


def test_parse_lines_cross_page_break() -> None:
    text = _make_kjv_text(
        "Genesis 1",
        "1 In the beginning\fGod created the heaven.",
    )
    books, _, _ = parse_lines(text)
    verses = books["Genesis"][1]
    assert len(verses) == 1
    assert "In the beginning" in verses[0][1]
    assert "God created" in verses[0][1]


def test_parse_lines_skips_cross_references() -> None:
    text = _make_kjv_text(
        "Genesis 1",
        "(John 1:1–5; Hebrews 11:1–3)",
        "1 In the beginning God created the heaven.",
    )
    books, _, _ = parse_lines(text)
    verse_text = books["Genesis"][1][0][1]
    assert "John" not in verse_text
    assert "beginning" in verse_text


def test_parse_lines_skips_footer() -> None:
    text = _make_kjv_text(
        "Genesis 1",
        "KJV  [Online]",
        "1 In the beginning God created the heaven.",
    )
    books, _, _ = parse_lines(text)
    verse_text = books["Genesis"][1][0][1]
    assert "KJV" not in verse_text


def test_parse_lines_filters_saying_markers() -> None:
    text = _make_kjv_text(
        "Proverbs 22",
        "17 Bow down thine ear, and hear the words of the wise.",
        "Saying 1",
        "18 For [it is] a pleasant thing.",
    )
    books, _, _ = parse_lines(text)
    assert "Proverbs" in books
    assert 22 in books["Proverbs"]
    verses = books["Proverbs"][22]
    assert len(verses) == 2
    assert verses[0][0] == 17
    assert verses[1][0] == 18
    assert "Saying" not in verses[0][1]
    assert "Saying" not in verses[1][1]


def test_parse_lines_captures_headings() -> None:
    text = _make_kjv_text(
        "Genesis 1",
        "The Creation",
        "1 In the beginning God created the heaven.",
    )
    _, headings, _ = parse_lines(text)
    gen1_headings = headings["Genesis"][1]
    assert len(gen1_headings) == 1
    assert gen1_headings[0] == (1, "The Creation")


def test_parse_lines_heading_mid_chapter() -> None:
    text = _make_kjv_text(
        "Genesis 1",
        "1 In the beginning God created the heaven.",
        "The First Day",
        "3 And God said, Let there be light.",
    )
    _, headings, _ = parse_lines(text)
    gen1_headings = headings["Genesis"][1]
    assert (3, "The First Day") in gen1_headings


def test_parse_lines_preserves_bracketed_words() -> None:
    text = _make_kjv_text(
        "Genesis 1",
        "2 And the earth [was] without form.",
    )
    books, _, _ = parse_lines(text)
    assert "[was]" in books["Genesis"][1][0][1]


def test_parse_lines_numbered_books() -> None:
    text = _make_kjv_text(
        "1 Samuel 1",
        "1 Now there was a certain man.",
        "Song of Solomon 8",
        "1 O that thou wert as my brother.",
    )
    books, _, _ = parse_lines(text)
    assert "1 Samuel" in books
    assert "Song of Solomon" in books


def test_parse_lines_psalm_rename() -> None:
    text = _make_kjv_text(
        "Psalm 23",
        "1 The LORD is my shepherd.",
    )
    _, _, renames = parse_lines(text)
    assert "Psalm -> Psalms" in renames


def test_parse_lines_rejects_empty_input() -> None:
    with pytest.raises(KjvParseError, match="no verse lines found"):
        parse_lines("")


def test_parse_lines_narrow_no_break_space() -> None:
    """The raw PDF format uses U+202F before verse text."""
    text = "Genesis 1\n1\n In the beginning God created the heaven.\n"
    books, _, _ = parse_lines(text)
    assert books["Genesis"][1] == [
        (1, "In the beginning God created the heaven.")
    ]


# ---- build_canonical_translation --------------------------------------------


def test_build_rejects_missing_book() -> None:
    books_data = {"Genesis": {1: [(1, "In the beginning.")]}}
    headings_data: dict = {}
    with pytest.raises(KjvParseError, match="missing book"):
        build_canonical_translation(books_data, headings_data)


def test_build_includes_headings() -> None:
    from soap_journal.core.bible.books import ALL_BOOKS

    books_data = {}
    headings_data = {}
    for spec in ALL_BOOKS:
        expected_chapters = {
            "Genesis": 50, "Exodus": 40, "Leviticus": 27, "Numbers": 36,
            "Deuteronomy": 34, "Joshua": 24, "Judges": 21, "Ruth": 4,
            "1 Samuel": 31, "2 Samuel": 24, "1 Kings": 22, "2 Kings": 25,
            "1 Chronicles": 29, "2 Chronicles": 36, "Ezra": 10,
            "Nehemiah": 13, "Esther": 10, "Job": 42, "Psalms": 150,
            "Proverbs": 31, "Ecclesiastes": 12, "Song of Solomon": 8,
            "Isaiah": 66, "Jeremiah": 52, "Lamentations": 5, "Ezekiel": 48,
            "Daniel": 12, "Hosea": 14, "Joel": 3, "Amos": 9, "Obadiah": 1,
            "Jonah": 4, "Micah": 7, "Nahum": 3, "Habakkuk": 3,
            "Zephaniah": 3, "Haggai": 2, "Zechariah": 14, "Malachi": 4,
            "Matthew": 28, "Mark": 16, "Luke": 24, "John": 21, "Acts": 28,
            "Romans": 16, "1 Corinthians": 16, "2 Corinthians": 13,
            "Galatians": 6, "Ephesians": 6, "Philippians": 4,
            "Colossians": 4, "1 Thessalonians": 5, "2 Thessalonians": 3,
            "1 Timothy": 6, "2 Timothy": 4, "Titus": 3, "Philemon": 1,
            "Hebrews": 13, "James": 5, "1 Peter": 5, "2 Peter": 3,
            "1 John": 5, "2 John": 1, "3 John": 1, "Jude": 1,
            "Revelation": 22,
        }
        ch_count = expected_chapters[spec.name]
        book_chapters: dict[int, list[tuple[int, str]]] = {}
        heading_chapters: dict[int, list[tuple[int, str]]] = {}
        for c in range(1, ch_count + 1):
            book_chapters[c] = [(1, "Test verse.")]
            heading_chapters[c] = []
        if spec.name == "Genesis":
            heading_chapters[1] = [(1, "The Creation")]
        books_data[spec.name] = book_chapters
        headings_data[spec.name] = heading_chapters

    translation = build_canonical_translation(books_data, headings_data)
    gen1 = translation.books[0].chapters[0]
    assert len(gen1.headings) == 1
    assert gen1.headings[0].before_verse == 1
    assert gen1.headings[0].text == "The Creation"


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
    partial_text = (
        "Genesis 1\n1 In the beginning God created the heaven.\n"
    )
    with patch("soap_journal.parsers.pdfmaker_format.read_pdf", return_value=partial_text):
        result = main(
            [str(tmp_path / "fake.pdf"), "--out", str(tmp_path / "out.json")]
        )
    assert result == 1


# ---- full-source integration tests ------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(not REAL_SOURCE.exists(), reason="KJV PDF not found")
class TestRealKjvSource:
    """Integration tests against the bundled KJV PDF."""

    @pytest.fixture(scope="class")
    def translation(self) -> tuple:
        from soap_journal.parsers.kjv import _read_pdf

        text = _read_pdf(REAL_SOURCE)
        t, renames = parse_kjv_source(text)
        return t, renames

    def test_66_books(self, translation: tuple) -> None:
        t, _ = translation
        assert len(t.books) == 66

    def test_1189_chapters(self, translation: tuple) -> None:
        t, _ = translation
        chapters = sum(len(b.chapters) for b in t.books)
        assert chapters == 1189

    def test_31102_verses(self, translation: tuple) -> None:
        t, _ = translation
        verses = sum(
            len(c.verses) for b in t.books for c in b.chapters
        )
        assert verses == 31102

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
        assert self._get_verse(translation, "Genesis", 1, 1) == (
            "In the beginning God created the heaven and the earth."
        )

    def test_spot_check_psalm_23_1(self, translation: tuple) -> None:
        text = self._get_verse(translation, "Psalms", 23, 1)
        assert text.startswith("A Psalm of David.")
        assert "The LORD [is] my shepherd" in text
        assert "I shall not want" in text

    def test_spot_check_john_3_16(self, translation: tuple) -> None:
        text = self._get_verse(translation, "John", 3, 16)
        assert "God so loved the world" in text
        assert "only begotten Son" in text
        assert "everlasting life" in text

    def test_spot_check_matt_5_3(self, translation: tuple) -> None:
        assert self._get_verse(translation, "Matthew", 5, 3) == (
            "Blessed [are] the poor in spirit: "
            "for theirs is the kingdom of heaven."
        )

    def test_spot_check_rev_22_21(self, translation: tuple) -> None:
        assert self._get_verse(translation, "Revelation", 22, 21) == (
            "The grace of our Lord Jesus Christ [be] with you all. Amen."
        )

    def test_has_headings(self, translation: tuple) -> None:
        t, _ = translation
        gen1 = t.books[0].chapters[0]
        assert len(gen1.headings) > 0
        heading_texts = [h.text for h in gen1.headings]
        assert "The Creation" in heading_texts

    def test_psalm_renamed(self, translation: tuple) -> None:
        _, renames = translation
        assert "Psalm -> Psalms" in renames

    def test_cli_writes_json(self, translation: tuple, tmp_path: Path) -> None:
        t, _ = translation
        out = tmp_path / "kjv.json"
        from soap_journal.parsers.kjv import _write_canonical_json

        _write_canonical_json(t, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["code"] == "KJV"
        assert len(data["books"]) == 66
