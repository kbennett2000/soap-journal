"""ESV parser CLI.

Converts a user-provided English Standard Version PDF into canonical
Bible JSON.

Source format
-------------
- 8,386-page chunked e-reader PDF (280x420pt pages).
- Chapter headers: ``<bookN>.<chN>. Chapter <chN>`` (e.g., ``1.1. Chapter 1``).
  These are the primary structural signal; book identity comes from
  the ``book_index`` (1-66) which maps directly to ALL_BOOKS.
- Verse markers: integer followed by trailing whitespace on its own line.
  Page numbers are bare integers without trailing whitespace and are ignored.
- Verse text: free-flowing prose on subsequent lines.
- Pericope headings in three forms:
  - Standalone: ``(The Creation of the World)`` on its own line.
  - Run-together with verse marker: ``4(The Creation of Man and Woman)``.
  - Multi-line: ``(Abraham and the Covenant of`` / ``Circumcision)``.
  - Heading fused with verse text: ``(The Lord Is My Shepherd)A Psalm of``.
- Inline footnotes concatenated into verse text with no delimiter.
  Heuristic extraction attempted for tail-positioned footnotes.
- 66 books, 1,189 chapters.
- No red-letter formatting.

Usage
-----
    python -m soap_journal.parsers.esv <source.pdf> --out <output.json>

**Copyright**: The ESV text is copyrighted by Crossway (2001).
The parser source code is MIT-licensed. The PDF and generated JSON
must NOT be committed.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pypdf
from pydantic import ValidationError

from soap_journal.core.bible.books import ALL_BOOKS
from soap_journal.parsers.schema import (
    CanonicalBook,
    CanonicalChapter,
    CanonicalFootnote,
    CanonicalHeading,
    CanonicalTranslation,
    CanonicalVerse,
)

ESV_CODE = "ESV"
ESV_NAME = "English Standard Version"
ESV_LANGUAGE = "en"
ESV_COPYRIGHT = (
    "Scripture quotations are from the ESV® Bible "
    "(The Holy Bible, English Standard Version®), "
    "copyright © 2001 by Crossway, a publishing ministry of "
    "Good News Publishers. Used by permission. All rights reserved."
)

_CHAPTER_HEADER_RE = re.compile(r"^(\d+)\.(\d+)\.\s+Chapter\s+(\d+)$")

_VERSE_WITH_PERICOPE_RE = re.compile(r"^(\d+)\((.+)\)$")

_CROSS_REF_RE = re.compile(r"^\(.*\d+:\d+.*\)$")

_STANDALONE_PERICOPE_RE = re.compile(r"^\((.+)\)$")

_HEADING_WITH_TEXT_RE = re.compile(r"^\((.+?)\)([A-Z].*)$")

_VERSE_MARKER_RE = re.compile(r"^(\d+)\s+$")

_TRAILING_VERSE_RE = re.compile(r"^(.+[.!?,;:\"')\]])(\d{1,3})\s*$")

_FOOTNOTE_SPLIT_RE = re.compile(
    r"(?<=[a-z.,;:!?)\]”’])"
    r"((?:Or |Hebrew |Greek |Aramaic |Septuagint|Vulgate|Syriac|"
    r"Masoretic Text|Compare |Probable reading|That is|A few |"
    r"Some manuscripts ).*)"
    r"$"
)


class EsvParseError(Exception):
    """Raised for any structural problem in the ESV source."""


BooksData = dict[str, dict[int, list[tuple[int, str]]]]
HeadingsData = dict[str, dict[int, list[tuple[int, str]]]]
FootnotesData = dict[str, dict[int, list[tuple[int, str]]]]


def _read_pdf(path: Path) -> str:
    """Extract text from every page of a PDF, joined with form-feeds."""
    reader = pypdf.PdfReader(path)
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\f".join(pages)


def _preprocess(text: str) -> list[str]:
    """Normalize extracted PDF text into logical lines."""
    return text.replace("\f", "\n").splitlines()


def _book_name_for_index(index: int) -> str:
    """Map ESV book index (1-66) to canonical book name."""
    if not 1 <= index <= 66:
        raise EsvParseError(f"book index {index} out of range 1-66")
    return ALL_BOOKS[index - 1].name


def _extract_footnote(verse_text: str) -> tuple[str, str | None]:
    """Attempt to split a trailing footnote from verse text.

    Returns ``(clean_text, footnote_text)`` where ``footnote_text``
    is ``None`` if no footnote was detected.  Only handles footnotes
    at the end of the verse text.
    """
    m = _FOOTNOTE_SPLIT_RE.search(verse_text)
    if m is None:
        return verse_text, None

    split_pos = m.start(1)
    clean = verse_text[:split_pos].rstrip()
    footnote = m.group(1).strip()

    if not clean or clean[-1].isspace():
        return verse_text, None

    return clean, footnote


def parse_lines(
    text: str,
) -> tuple[BooksData, HeadingsData, FootnotesData, list[str]]:
    """Parse preprocessed ESV text into intermediate data structures."""
    raw_lines = _preprocess(text)

    books_data: BooksData = {}
    headings_data: HeadingsData = {}
    footnotes_data: FootnotesData = {}
    warnings: list[str] = []

    current_book: str | None = None
    current_chapter: int = 0
    current_verse: int = 0
    current_text_parts: list[str] = []
    pending_headings: list[str] = []
    pericope_buffer: str | None = None
    pericope_verse: int = 0
    started: bool = False

    def _flush_verse() -> None:
        nonlocal current_verse
        if current_book is None or current_verse == 0:
            return
        assembled = " ".join(current_text_parts).strip()
        if not assembled:
            return

        clean_text, footnote_text = _extract_footnote(assembled)
        chapter_verses = books_data[current_book][current_chapter]
        chapter_verses.append((current_verse, clean_text))

        if footnote_text:
            chapter_fns = footnotes_data[current_book][current_chapter]
            chapter_fns.append((current_verse, footnote_text))

        current_verse = 0
        current_text_parts.clear()

    def _flush_headings(before_verse: int) -> None:
        if not pending_headings or current_book is None:
            return
        chapter_heads = headings_data[current_book][current_chapter]
        for h in pending_headings:
            chapter_heads.append((before_verse, h))
        pending_headings.clear()

    for raw in raw_lines:
        stripped = raw.strip()
        if not stripped:
            continue

        # Handle multi-line pericope continuation
        if pericope_buffer is not None:
            pericope_buffer += " " + stripped
            if stripped.endswith(")"):
                paren_start = pericope_buffer.index("(")
                heading = pericope_buffer[paren_start + 1 : -1]
                if pericope_verse > 0:
                    _flush_verse()
                    pending_headings.append(heading)
                    _flush_headings(pericope_verse)
                    current_verse = pericope_verse
                    current_text_parts.clear()
                else:
                    pending_headings.append(heading)
                pericope_buffer = None
                pericope_verse = 0
            continue

        # 1. Chapter header
        m = _CHAPTER_HEADER_RE.match(stripped)
        if m:
            book_index = int(m.group(1))
            ch_from_pattern = int(m.group(2))
            ch_from_label = int(m.group(3))
            if ch_from_pattern != ch_from_label:
                raise EsvParseError(
                    f"chapter header mismatch: pattern says {ch_from_pattern}, "
                    f"label says {ch_from_label}"
                )
            _flush_verse()
            if pending_headings and current_verse > 0:
                _flush_headings(current_verse)

            canonical = _book_name_for_index(book_index)
            current_book = canonical
            current_chapter = ch_from_pattern
            current_verse = 0
            current_text_parts.clear()
            pending_headings.clear()
            books_data.setdefault(canonical, {}).setdefault(current_chapter, [])
            headings_data.setdefault(canonical, {}).setdefault(current_chapter, [])
            footnotes_data.setdefault(canonical, {}).setdefault(current_chapter, [])
            started = True
            continue

        if not started:
            continue

        # 2. Verse with pericope: "4(The Creation of Man and Woman)"
        m = _VERSE_WITH_PERICOPE_RE.match(stripped)
        if m:
            verse_num = int(m.group(1))
            heading_text = m.group(2)
            _flush_verse()
            pending_headings.append(heading_text)
            _flush_headings(verse_num)
            current_verse = verse_num
            current_text_parts.clear()
            continue

        # 2b. Multi-line verse+pericope: "35(A Prophet Condemns Ben-hadad's"
        m = re.match(r"^(\d+)\((.+)$", stripped)
        if m and not stripped.endswith(")"):
            pericope_buffer = stripped
            pericope_verse = int(m.group(1))
            continue

        # 3. Cross-reference: "(Genesis 22:1-10)" — skip
        if _CROSS_REF_RE.match(stripped):
            continue

        # 3b. Heading fused with text: "(The Lord Is My Shepherd)A Psalm of"
        m = _HEADING_WITH_TEXT_RE.match(stripped)
        if m:
            heading_text = m.group(1)
            verse_text_start = m.group(2)
            if current_verse > 0:
                _flush_headings(current_verse)
                pending_headings.append(heading_text)
                _flush_headings(current_verse)
                current_text_parts.append(verse_text_start)
            else:
                pending_headings.append(heading_text)
            continue

        # 4. Standalone pericope: "(The Creation of the World)"
        #    Exclude parenthesized verse text like "(Now they had been sent
        #    from the Pharisees.)" — these end with a period inside parens.
        m = _STANDALONE_PERICOPE_RE.match(stripped)
        if m:
            content = m.group(1)
            if not content.rstrip().endswith("."):
                if current_verse > 0 and current_text_parts:
                    _flush_verse()
                pending_headings.append(content)
                continue

        # 5. Multi-line pericope start: "(Abraham and the Covenant of"
        #    Only buffer when before the first verse in a chapter to avoid
        #    eating verse text that starts with parenthetical content.
        if stripped.startswith("(") and ")" not in stripped and current_verse == 0:
            pericope_buffer = stripped
            pericope_verse = 0
            continue

        # 6. Verse number fused with section label: "9Beth", "161Sin and Shin"
        m = re.match(r"^(\d+)([A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+)?)$", stripped)
        if m:
            verse_num = int(m.group(1))
            section_label = m.group(2)
            _flush_verse()
            pending_headings.append(section_label)
            _flush_headings(verse_num)
            current_verse = verse_num
            current_text_parts.clear()
            continue

        # 7. Verse marker (digits with trailing whitespace)
        m = _VERSE_MARKER_RE.match(raw)
        if m:
            verse_num = int(m.group(1))
            _flush_verse()
            _flush_headings(verse_num)
            current_verse = verse_num
            current_text_parts.clear()
            continue

        # 8. Page number (bare integer, no trailing space) — skip
        if re.fullmatch(r"\d+", stripped):
            continue

        # 8b. Verse marker fused with text (no space): "19in which..."
        m = re.match(r"^(\d+)(\S.+)$", stripped)
        if m and current_verse > 0:
            fused_num = int(m.group(1))
            fused_text = m.group(2)
            if fused_num == current_verse + 1:
                _flush_verse()
                _flush_headings(fused_num)
                current_verse = fused_num
                current_text_parts.clear()
                current_text_parts.append(fused_text)
                continue

        # 9. Verse text (check for trailing fused verse marker)
        if current_verse > 0:
            m = _TRAILING_VERSE_RE.match(stripped)
            if m:
                next_verse = int(m.group(2))
                if next_verse == current_verse + 1:
                    text_part = m.group(1)
                    current_text_parts.append(text_part)
                    _flush_verse()
                    _flush_headings(next_verse)
                    current_verse = next_verse
                    current_text_parts.clear()
                else:
                    current_text_parts.append(stripped)
            else:
                current_text_parts.append(stripped)

    _flush_verse()

    if not books_data:
        raise EsvParseError("no verse lines found")

    return books_data, headings_data, footnotes_data, warnings


def build_canonical_translation(
    books_data: BooksData,
    headings_data: HeadingsData,
    footnotes_data: FootnotesData,
) -> CanonicalTranslation:
    """Assemble a validated CanonicalTranslation from parsed ESV data."""
    canonical_books: list[CanonicalBook] = []
    for spec in ALL_BOOKS:
        chapters_dict = books_data.get(spec.name)
        if not chapters_dict:
            raise EsvParseError(f"source is missing book {spec.name!r}")

        chapters_sorted: list[CanonicalChapter] = []
        for chapter_number in sorted(chapters_dict.keys()):
            verses = sorted(chapters_dict[chapter_number], key=lambda t: t[0])

            chapter_headings_raw = headings_data.get(spec.name, {}).get(chapter_number, [])
            headings = [CanonicalHeading(before_verse=bv, text=t) for bv, t in chapter_headings_raw]

            chapter_footnotes_raw = footnotes_data.get(spec.name, {}).get(chapter_number, [])
            footnotes = [
                CanonicalFootnote(verse_number=vn, text=t) for vn, t in chapter_footnotes_raw
            ]

            chapters_sorted.append(
                CanonicalChapter(
                    number=chapter_number,
                    verses=[CanonicalVerse(number=n, text=t) for n, t in verses],
                    headings=headings,
                    footnotes=footnotes,
                )
            )
        canonical_books.append(
            CanonicalBook(
                name=spec.name,
                abbreviation=spec.abbreviation,
                order_index=spec.order_index,
                chapters=chapters_sorted,
            )
        )

    return CanonicalTranslation(
        code=ESV_CODE,
        name=ESV_NAME,
        language=ESV_LANGUAGE,
        copyright=ESV_COPYRIGHT,
        books=canonical_books,
    )


def parse_esv_source(text: str) -> tuple[CanonicalTranslation, list[str]]:
    """Parse ESV text into a fully-validated CanonicalTranslation."""
    books_data, headings_data, footnotes_data, warnings = parse_lines(text)
    return (
        build_canonical_translation(books_data, headings_data, footnotes_data),
        warnings,
    )


def _write_canonical_json(translation: CanonicalTranslation, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(translation.model_dump_json(indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m soap_journal.parsers.esv",
        description="Parse an ESV PDF into canonical Bible JSON.",
    )
    parser.add_argument("source", type=Path, help="Path to the ESV PDF")
    parser.add_argument("--out", type=Path, required=True, help="Output path for canonical JSON")
    args = parser.parse_args(argv)

    try:
        source_text = _read_pdf(args.source)
    except OSError as exc:
        print(f"error: cannot read source: {exc}", file=sys.stderr)
        return 2
    except pypdf.errors.PyPdfError as exc:
        print(f"error: cannot parse PDF: {exc}", file=sys.stderr)
        return 2

    try:
        translation, warnings = parse_esv_source(source_text)
    except EsvParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ValidationError as exc:
        print(
            f"error: canonical schema validation failed:\n{exc}",
            file=sys.stderr,
        )
        return 1

    _write_canonical_json(translation, args.out)
    for w in warnings:
        print(f"warning: {w}")
    chapters = sum(len(b.chapters) for b in translation.books)
    verses = sum(len(c.verses) for b in translation.books for c in b.chapters)
    fn_count = sum(len(c.footnotes) for b in translation.books for c in b.chapters)
    h_count = sum(len(c.headings) for b in translation.books for c in b.chapters)
    print(
        f"Parsed {translation.code}: {len(translation.books)} books, "
        f"{chapters} chapters, {verses} verses, "
        f"{h_count} headings, {fn_count} footnotes -> {args.out}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - thin shell
    raise SystemExit(main())
