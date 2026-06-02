"""Tests for the NET parser internals and the canonical adapter.

The pure-function unit tests (classify / group_into_lines / extract_cross_refs)
are ported from the private repo's parser tests. The adapter tests cover the
ChapterData -> canonical mapping (placeholder fill, typed notes, cross-ref
resolution, char_offset clamping). One PDF-backed smoke test parses Genesis 1
from the user-supplied bibles/net.pdf when it is present.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from soap_journal.core.bible.books import ALL_BOOKS
from soap_journal.parsers.net import (
    _ORDER_BY_ABBREV,
    NetParseError,
    _chapter_to_canonical,
    _cross_ref_to_canonical,
    build_canonical_translation,
)
from soap_journal.parsers.net_pdf import (
    _BOOK_ABBREVS,
    ChapterData,
    CrossRefData,
    NoteRow,
    VerseRow,
    Word,
    WordCategory,
    classify,
    extract_cross_refs,
    group_into_lines,
    parse_chapter,
)

# bibles/ lives at the repo root; this file is backend/soap_journal/parsers/.
_NET_PDF = Path(__file__).resolve().parents[3] / "bibles" / "net.pdf"


# ---- classify (ported) -----------------------------------------------------


def test_classify_verse_body() -> None:
    assert classify("In", 12.5) == WordCategory.VERSE_BODY


def test_classify_section_heading() -> None:
    assert classify("World", 12.0) == WordCategory.SECTION_HEADING


def test_classify_verse_marker() -> None:
    assert classify("1:1", 11.3) == WordCategory.VERSE_MARKER


def test_classify_cross_ref_in_note_body_is_not_a_verse_marker() -> None:
    # A "1:1" rendered at note-body height is a cross-reference, not a marker.
    assert classify("1:1", 9.6) == WordCategory.NOTE_BODY


def test_classify_marker_super() -> None:
    assert classify("10", 7.0) == WordCategory.MARKER_SUPER
    assert classify("*", 7.1) == WordCategory.MARKER_SUPER


def test_classify_type_code() -> None:
    assert classify("tn", 8.5) == WordCategory.TYPE_CODE
    assert classify("sn", 8.5) == WordCategory.TYPE_CODE


def test_classify_book_title() -> None:
    assert classify("Genesis", 56.1) == WordCategory.BOOK_TITLE


# ---- group_into_lines (ported) ---------------------------------------------


def _w(x: float, y: float, h: float, text: str) -> Word:
    return Word(x=x, y=y, h=h, text=text, column=0, category=WordCategory.VERSE_BODY)


def test_group_into_lines_groups_close_y() -> None:
    words = [_w(10, 100, 12, "A"), _w(30, 100.5, 12, "B"), _w(10, 110, 12, "C")]
    lines = group_into_lines(words)
    assert len(lines) == 2
    assert [w.text for w in lines[0]] == ["A", "B"]
    assert [w.text for w in lines[1]] == ["C"]


def test_group_into_lines_empty() -> None:
    assert group_into_lines([]) == []


# ---- extract_cross_refs (ported) -------------------------------------------


def test_extract_cross_refs_single() -> None:
    refs = extract_cross_refs("See Gen 2:4 for context.")
    assert refs == [CrossRefData("Gen", 2, 4, None)]


def test_extract_cross_refs_with_range() -> None:
    refs = extract_cross_refs("Compare John 1:1-3.")
    assert refs == [CrossRefData("John", 1, 1, 3)]


def test_extract_cross_refs_multi_word_book() -> None:
    refs = extract_cross_refs("In 1 Sam 10:10 we read…")
    assert refs == [CrossRefData("1 Sam", 10, 10, None)]


def test_extract_cross_refs_dedupes() -> None:
    refs = extract_cross_refs("Gen 1:1 (cf. Gen 1:1)")
    assert refs == [CrossRefData("Gen", 1, 1, None)]


def test_extract_cross_refs_multiple_books() -> None:
    refs = extract_cross_refs("see Ps 33:9, John 1:1-3, 1 Cor 8:6, and Col 1:16.")
    short_names = {r.to_book_short for r in refs}
    assert {"Ps", "John", "1 Cor", "Col"} <= short_names


# ---- abbreviation table -> canonical order ---------------------------------


def test_book_abbrevs_align_with_canonical_order() -> None:
    # The whole cross-ref resolution rests on index+1 == canonical order_index.
    assert len(_BOOK_ABBREVS) == 66
    for i, abbrev in enumerate(_BOOK_ABBREVS):
        assert _ORDER_BY_ABBREV[abbrev] == i + 1
        assert ALL_BOOKS[i].order_index == i + 1


def test_cross_ref_resolution_maps_to_order_index() -> None:
    ref = _cross_ref_to_canonical(CrossRefData("John", 1, 1, 3))
    assert ref.to_book_order_index == 43  # John
    assert (ref.to_chapter, ref.to_verse_start, ref.to_verse_end) == (1, 1, 3)


def test_cross_ref_resolution_fails_loud_on_unknown_abbrev() -> None:
    with pytest.raises(NetParseError):
        _cross_ref_to_canonical(CrossRefData("Nope", 1, 1, None))


# ---- adapter: ChapterData -> CanonicalChapter ------------------------------


def _gen1_chapterdata() -> ChapterData:
    # Genesis 1 with a gap at verse 2 (to exercise placeholder fill) and a typed,
    # anchored note on verse 1 carrying two cross-refs.
    return ChapterData(
        book_short="Gen",
        book_full="Genesis",
        book_position=1,
        testament="OT",
        chapter=1,
        verses=[VerseRow(1, "In the beginning"), VerseRow(3, "And God said")],
        headings=[(1, "The Creation")],
        notes=[
            NoteRow(
                verse_number=1,
                chapter=1,
                marker=1,
                word_offset=2,
                type="tn",
                body="The Hebrew term; cf. Gen 2:4 and John 1:1-3.",
                ordinal=0,
                cross_refs=[CrossRefData("Gen", 2, 4, None), CrossRefData("John", 1, 1, 3)],
            )
        ],
    )


def test_adapter_fills_omitted_verses_with_placeholder() -> None:
    chapter, _ = _chapter_to_canonical(_gen1_chapterdata())
    assert [v.number for v in chapter.verses] == [1, 2, 3]
    assert chapter.verses[1].text == "[verse not included in the NET]"
    assert chapter.verses[0].text == "In the beginning"


def test_adapter_maps_typed_note_and_cross_refs() -> None:
    chapter, stats = _chapter_to_canonical(_gen1_chapterdata())
    assert stats.dropped_cross_refs == 0
    assert len(chapter.footnotes) == 1
    fn = chapter.footnotes[0]
    assert fn.verse_number == 1
    assert fn.note_type == "tn"
    assert fn.char_offset == 2
    assert fn.marker == 1
    assert fn.ordinal == 0
    assert fn.text.startswith("The Hebrew term")
    resolved = [
        (c.to_book_order_index, c.to_chapter, c.to_verse_start, c.to_verse_end)
        for c in fn.cross_refs
    ]
    assert resolved == [(1, 2, 4, None), (43, 1, 1, 3)]
    assert len(chapter.headings) == 1
    assert chapter.headings[0].before_verse == 1


def test_adapter_clamps_char_offset_past_placeholder_to_none() -> None:
    # A note on an omitted verse (placeholder shorter than the original) whose
    # word_offset points past the placeholder text must drop its anchor.
    cd = ChapterData(
        book_short="Gen",
        book_full="Genesis",
        book_position=1,
        testament="OT",
        chapter=1,
        verses=[VerseRow(1, "In the beginning"), VerseRow(3, "And God said")],
        notes=[
            NoteRow(
                verse_number=2,  # placeholder verse
                chapter=1,
                marker=1,
                word_offset=999,
                type="tc",
                body="This verse is not included in the NET.",
                ordinal=0,
            )
        ],
    )
    chapter, _ = _chapter_to_canonical(cd)
    assert len(chapter.footnotes) == 1
    assert chapter.footnotes[0].verse_number == 2
    assert chapter.footnotes[0].char_offset is None


def test_adapter_fills_present_but_empty_verse_with_distinct_placeholder() -> None:
    # A verse present in the parse but with empty text (e.g. the Acts letter
    # passages) gets the distinct "not captured" placeholder and is counted.
    cd = ChapterData(
        book_short="Gen",
        book_full="Genesis",
        book_position=1,
        testament="OT",
        chapter=1,
        verses=[VerseRow(1, "In the beginning"), VerseRow(2, "   ")],
    )
    chapter, stats = _chapter_to_canonical(cd)
    assert stats.uncaptured_verses == 1
    assert chapter.verses[1].text == "[verse text not captured]"


def test_adapter_drops_malformed_cross_ref() -> None:
    # A backwards range (to_verse_end < to_verse_start) is unusable; the adapter
    # drops it (counted) instead of letting it abort the whole parse.
    cd = ChapterData(
        book_short="Gen",
        book_full="Genesis",
        book_position=1,
        testament="OT",
        chapter=1,
        verses=[VerseRow(1, "In the beginning")],
        notes=[
            NoteRow(
                verse_number=1,
                chapter=1,
                marker=1,
                word_offset=2,
                type="tn",
                body="a note with a junk range",
                ordinal=0,
                cross_refs=[CrossRefData("Lev", 25, 52, 15)],  # end < start
            )
        ],
    )
    chapter, stats = _chapter_to_canonical(cd)
    assert stats.dropped_cross_refs == 1
    assert chapter.footnotes[0].cross_refs == []


def test_build_canonical_translation_requires_all_66_books() -> None:
    # Only Genesis present -> the 66-book assembly must fail loud.
    with pytest.raises(NetParseError):
        build_canonical_translation([_gen1_chapterdata()])


# ---- live smoke test (PDF-backed) ------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(not _NET_PDF.exists(), reason="bibles/net.pdf not present")
def test_smoke_parse_genesis_1() -> None:
    chapter = parse_chapter(
        pdf_path=_NET_PDF,
        book_short="Gen",
        book_full="Genesis",
        book_position=1,
        testament="OT",
        chapter=1,
        page_range=(29, 33),
    )
    assert len(chapter.verses) == 31
    assert [v.number for v in chapter.verses] == list(range(1, 32))
    assert chapter.verses[0].text.startswith("In the beginning God created")
    # A section heading precedes verse 1.
    assert any(before_verse == 1 for (before_verse, _text) in chapter.headings)
    # Verse 1 carries notes, and the chapter has cross-refs overall.
    assert any(n.verse_number == 1 for n in chapter.notes)
    assert sum(len(n.cross_refs) for n in chapter.notes) >= 1
