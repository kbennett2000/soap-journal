"""NET Bible parser CLI.

Converts the user-provided NET Bible Translator's Edition PDF into canonical
Bible JSON, carrying the NET's typed, character-anchored translator's notes
(tn/sn/tc/map) and the cross-references embedded in them.

Source format
-------------
- 2,539-page two-column PDF (441x666pt), the NET Translator's Edition.
- Parsed one book at a time over its PDF page range (the ``BOOKS`` table below),
  from the bbox-layout XHTML that ``pdftotext -bbox-layout`` emits. The parser
  internals — font-height classification, column split, marker/note matching —
  live in ``net_pdf`` and were tuned empirically against this edition.
- Notes are typed, anchored to a character offset in the verse, ordered within
  the verse, and may contain cross-references to other verses.
- The NET omits a handful of disputed verses (e.g. Acts 8:37, John 5:4); those
  numbers are filled with placeholder text so the canonical 1..N invariant holds
  and verse numbers stay aligned with the other translations — the same approach
  ``nlt.py`` already uses.

Usage
-----
    python -m soap_journal.parsers.net <source.pdf> --out <output.json>

**Prerequisite**: ``pdftotext`` from poppler-utils must be on ``PATH``.

**Copyright**: The NET Bible text is copyrighted by Biblical Studies Press,
L.L.C. The parser source code is MIT-licensed. The PDF and generated JSON must
NOT be committed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from soap_journal.core.bible.books import ALL_BOOKS
from soap_journal.parsers.net_pdf import (
    _BOOK_ABBREVS,
    ChapterData,
    CrossRefData,
    parse_book,
)
from soap_journal.parsers.schema import (
    CanonicalBook,
    CanonicalChapter,
    CanonicalCrossRef,
    CanonicalFootnote,
    CanonicalHeading,
    CanonicalTranslation,
    CanonicalVerse,
)

NET_CODE = "NET"
NET_NAME = "New English Translation"
NET_LANGUAGE = "en"
NET_COPYRIGHT = (
    "Scripture quoted by permission. Quotations designated (NET) are from the "
    "NET Bible® copyright ©1996, 2019 by Biblical Studies Press, L.L.C. "
    "http://netbible.com All rights reserved."
)

# Text inserted for verse numbers the NET omits (disputed / Majority-Text-only
# verses such as Acts 8:37 and John 5:4). Keeps the canonical 1..N invariant and
# cross-translation verse alignment intact. Mirrors nlt.py's placeholder.
_OMITTED_VERSE_PLACEHOLDER = "[verse not included in the NET]"

# Per-book PDF page table, ported verbatim from the private repo's
# ingest/__main__.py. Fields: short, full, position, testament, n_chapters,
# first_pdf_page. The end page of each book is the next book's first page minus
# one (Revelation runs to END_OF_BIBLE_PDF_PAGE).
BOOKS: list[tuple[str, str, int, str, int, int]] = [
    ("Gen", "Genesis", 1, "OT", 50, 29),
    ("Exod", "Exodus", 2, "OT", 40, 140),
    ("Lev", "Leviticus", 3, "OT", 27, 254),
    ("Num", "Numbers", 4, "OT", 36, 316),
    ("Deut", "Deuteronomy", 5, "OT", 34, 391),
    ("Josh", "Joshua", 6, "OT", 24, 448),
    ("Judg", "Judges", 7, "OT", 21, 479),
    ("Ruth", "Ruth", 8, "OT", 4, 517),
    ("1 Sam", "1 Samuel", 9, "OT", 31, 531),
    ("2 Sam", "2 Samuel", 10, "OT", 24, 571),
    ("1 Kgs", "1 Kings", 11, "OT", 22, 611),
    ("2 Kgs", "2 Kings", 12, "OT", 25, 653),
    ("1 Chr", "1 Chronicles", 13, "OT", 29, 695),
    ("2 Chr", "2 Chronicles", 14, "OT", 36, 732),
    ("Ezra", "Ezra", 15, "OT", 10, 775),
    ("Neh", "Nehemiah", 16, "OT", 13, 790),
    ("Esth", "Esther", 17, "OT", 10, 809),
    ("Job", "Job", 18, "OT", 42, 821),
    ("Ps", "Psalms", 19, "OT", 150, 926),
    ("Prov", "Proverbs", 20, "OT", 31, 1101),
    ("Eccl", "Ecclesiastes", 21, "OT", 12, 1210),
    ("Song", "Song of Songs", 22, "OT", 8, 1252),
    ("Isa", "Isaiah", 23, "OT", 66, 1288),
    ("Jer", "Jeremiah", 24, "OT", 52, 1404),
    ("Lam", "Lamentations", 25, "OT", 5, 1578),
    ("Ezek", "Ezekiel", 26, "OT", 48, 1605),
    ("Dan", "Daniel", 27, "OT", 12, 1671),
    ("Hos", "Hosea", 28, "OT", 14, 1696),
    ("Joel", "Joel", 29, "OT", 3, 1723),
    ("Amos", "Amos", 30, "OT", 9, 1732),
    ("Obad", "Obadiah", 31, "OT", 1, 1750),
    ("Jonah", "Jonah", 32, "OT", 4, 1755),
    ("Mic", "Micah", 33, "OT", 7, 1767),
    ("Nah", "Nahum", 34, "OT", 3, 1779),
    ("Hab", "Habakkuk", 35, "OT", 3, 1797),
    ("Zeph", "Zephaniah", 36, "OT", 3, 1804),
    ("Hag", "Haggai", 37, "OT", 2, 1811),
    ("Zech", "Zechariah", 38, "OT", 14, 1815),
    ("Mal", "Malachi", 39, "OT", 4, 1829),
    ("Matt", "Matthew", 40, "NT", 28, 1835),
    ("Mark", "Mark", 41, "NT", 16, 1895),
    ("Luke", "Luke", 42, "NT", 24, 1939),
    ("John", "John", 43, "NT", 21, 2044),
    ("Acts", "Acts", 44, "NT", 28, 2131),
    ("Rom", "Romans", 45, "NT", 16, 2233),
    ("1 Cor", "1 Corinthians", 46, "NT", 16, 2257),
    ("2 Cor", "2 Corinthians", 47, "NT", 13, 2277),
    ("Gal", "Galatians", 48, "NT", 6, 2293),
    ("Eph", "Ephesians", 49, "NT", 6, 2305),
    ("Phil", "Philippians", 50, "NT", 4, 2319),
    ("Col", "Colossians", 51, "NT", 4, 2326),
    ("1 Thess", "1 Thessalonians", 52, "NT", 5, 2335),
    ("2 Thess", "2 Thessalonians", 53, "NT", 3, 2341),
    ("1 Tim", "1 Timothy", 54, "NT", 6, 2345),
    ("2 Tim", "2 Timothy", 55, "NT", 4, 2353),
    ("Titus", "Titus", 56, "NT", 3, 2358),
    ("Phlm", "Philemon", 57, "NT", 1, 2361),
    ("Heb", "Hebrews", 58, "NT", 13, 2364),
    ("Jas", "James", 59, "NT", 5, 2379),
    ("1 Pet", "1 Peter", 60, "NT", 5, 2385),
    ("2 Pet", "2 Peter", 61, "NT", 3, 2394),
    ("1 John", "1 John", 62, "NT", 5, 2404),
    ("2 John", "2 John", 63, "NT", 1, 2425),
    ("3 John", "3 John", 64, "NT", 1, 2427),
    ("Jude", "Jude", 65, "NT", 1, 2430),
    ("Rev", "Revelation", 66, "NT", 22, 2435),
]
END_OF_BIBLE_PDF_PAGE = 2474  # Page 2475 begins the "Principles of Translation" appendix.

# Map a NET cross-ref abbreviation to a canonical 1..66 order_index. _BOOK_ABBREVS
# is in canonical order, so index + 1 is the order_index (verified against
# ALL_BOOKS in the tests).
_ORDER_BY_ABBREV: dict[str, int] = {abbrev: i + 1 for i, abbrev in enumerate(_BOOK_ABBREVS)}


class NetParseError(Exception):
    """Raised for any structural problem assembling the NET canonical output."""


def _cross_ref_to_canonical(xr: CrossRefData) -> CanonicalCrossRef:
    """Resolve a NET cross-ref's book abbreviation to a canonical order_index."""
    order = _ORDER_BY_ABBREV.get(xr.to_book_short)
    if order is None:
        # By construction every to_book_short comes from _BOOK_ABBREVS; fail loud
        # if that ever stops holding.
        raise NetParseError(
            f"cross-ref book abbreviation {xr.to_book_short!r} is not in the NET book table"
        )
    return CanonicalCrossRef(
        to_book_order_index=order,
        to_chapter=xr.to_chapter,
        to_verse_start=xr.to_verse_start,
        to_verse_end=xr.to_verse_end,
    )


def _chapter_to_canonical(chapter: ChapterData) -> CanonicalChapter:
    """Map a parsed ChapterData to a validated CanonicalChapter.

    Fills omitted verse numbers with placeholder text (so verses are 1..N
    contiguous), maps typed notes and their cross-refs, and drops a note's
    char_offset if it would point past the (possibly placeholder) verse text.
    """
    verse_text = {v.number: v.text for v in chapter.verses}
    max_v = max(verse_text) if verse_text else 0
    canon_verses = [
        CanonicalVerse(number=v, text=verse_text.get(v, _OMITTED_VERSE_PLACEHOLDER))
        for v in range(1, max_v + 1)
    ]
    verse_len = {v.number: len(v.text) for v in canon_verses}

    footnotes: list[CanonicalFootnote] = []
    for note in chapter.notes:
        vlen = verse_len.get(note.verse_number)
        if vlen is None:
            # Note references a verse number outside 1..N (e.g. trailing artifact);
            # it cannot be anchored to an existing verse, so skip it.
            continue
        # A char_offset past the verse text (e.g. a tc note on an omitted verse
        # whose placeholder is shorter) would fail the chapter validator — drop
        # the anchor rather than the note.
        char_offset = note.word_offset if note.word_offset <= vlen else None
        footnotes.append(
            CanonicalFootnote(
                verse_number=note.verse_number,
                text=note.body,
                note_type=note.type,
                char_offset=char_offset,
                marker=note.marker,
                ordinal=note.ordinal,
                cross_refs=[_cross_ref_to_canonical(xr) for xr in note.cross_refs],
            )
        )

    headings = [
        CanonicalHeading(before_verse=before_verse, text=text)
        for (before_verse, text) in chapter.headings
        if before_verse in verse_len
    ]

    return CanonicalChapter(
        number=chapter.chapter,
        verses=canon_verses,
        headings=headings,
        footnotes=footnotes,
    )


def build_canonical_translation(chapters: list[ChapterData]) -> CanonicalTranslation:
    """Assemble a validated CanonicalTranslation from parsed NET chapter data.

    Chapters are grouped by `book_position`, which equals the canonical
    `order_index`; each book is built from SOAP's canonical name/abbreviation
    (joining on order, not NET's names — sidesteps name reconciliation, e.g. NET
    "Song of Songs" vs canonical "Song of Solomon").
    """
    by_position: dict[int, list[ChapterData]] = {}
    for chapter in chapters:
        by_position.setdefault(chapter.book_position, []).append(chapter)

    canonical_books: list[CanonicalBook] = []
    for spec in ALL_BOOKS:
        book_chapters = by_position.get(spec.order_index)
        if not book_chapters:
            raise NetParseError(f"parse produced no chapters for {spec.name!r}")
        canon_chapters = [
            _chapter_to_canonical(c) for c in sorted(book_chapters, key=lambda c: c.chapter)
        ]
        canonical_books.append(
            CanonicalBook(
                name=spec.name,
                abbreviation=spec.abbreviation,
                order_index=spec.order_index,
                chapters=canon_chapters,
            )
        )

    return CanonicalTranslation(
        code=NET_CODE,
        name=NET_NAME,
        language=NET_LANGUAGE,
        copyright=NET_COPYRIGHT,
        books=canonical_books,
    )


def parse_net_pdf(pdf_path: Path) -> CanonicalTranslation:
    """Parse the whole NET PDF into a validated CanonicalTranslation.

    Drives `net_pdf.parse_book` once per book over its page range (one
    `pdftotext` invocation per book), then runs the canonical adapter.
    """
    all_chapters: list[ChapterData] = []
    for idx, (short, full, position, testament, n_chapters, first_pdf) in enumerate(BOOKS):
        last_pdf = BOOKS[idx + 1][5] - 1 if idx + 1 < len(BOOKS) else END_OF_BIBLE_PDF_PAGE
        all_chapters.extend(
            parse_book(
                pdf_path=pdf_path,
                book_short=short,
                book_full=full,
                book_position=position,
                testament=testament,  # type: ignore[arg-type]
                page_range=(first_pdf, last_pdf),
                max_chapter=n_chapters,
            )
        )
    return build_canonical_translation(all_chapters)


def _write_canonical_json(translation: CanonicalTranslation, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(translation.model_dump_json(indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m soap_journal.parsers.net",
        description="Parse a NET Bible PDF into canonical Bible JSON.",
    )
    parser.add_argument("source", type=Path, help="Path to the NET Bible PDF")
    parser.add_argument("--out", type=Path, required=True, help="Output path for canonical JSON")
    args = parser.parse_args(argv)

    try:
        translation = parse_net_pdf(args.source)
    except FileNotFoundError:
        print("error: pdftotext not found; install poppler-utils", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: cannot read source: {exc}", file=sys.stderr)
        return 2
    except NetParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ValidationError as exc:
        print(f"error: canonical schema validation failed:\n{exc}", file=sys.stderr)
        return 1

    _write_canonical_json(translation, args.out)
    chapters = sum(len(b.chapters) for b in translation.books)
    verses = sum(len(c.verses) for b in translation.books for c in b.chapters)
    print(
        f"Parsed {translation.code}: {len(translation.books)} books, "
        f"{chapters} chapters, {verses} verses -> {args.out}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - thin shell
    raise SystemExit(main())
