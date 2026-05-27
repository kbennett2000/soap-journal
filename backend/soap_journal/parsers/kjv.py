"""KJV parser CLI.

Converts a public-domain King James Version PDF into canonical Bible JSON.

Source format
-------------
- 1517-page PDF with embedded Tahoma / Times fonts, Unicode mappings.
- Pages 1–2 are TOC / title.  Real scripture starts at "Genesis 1".
- Chapter markers are dedicated lines: ``Genesis 1``, ``1 Samuel 31``,
  ``Song of Solomon 8``, ``Psalm 150``.
- Verse numbers sit at the end of lines (or on their own line) followed
  by U+202F (narrow no-break space) at the start of the next line.
  After preprocessing, verses appear inline: ``1 In the beginning … 2 And``.
- Section headings (``The Creation``, ``The First Day``) are interleaved
  between chapter headers and verse text.
- Parenthetical cross-reference lines like ``(John 1:1–5; Hebrews 11:1–3)``
  appear under headings; skipped.
- ``KJV  [Online]`` footer appears between books; skipped.
- ``Saying N`` sub-section markers in Proverbs (30 of them) look like
  chapter headers but ``Saying`` is not a canonical book name; filtered
  by checking ``get_book_by_name()``.
- Bracketed italics ``[was]``, ``[is]`` preserved verbatim.
- Form-feed characters mark page breaks; treated as line separators.
- 66 books, 1,189 chapters, 31,102 verses.
- No red-letter formatting or footnotes.

Usage
-----
    python -m soap_journal.parsers.kjv <source.pdf> --out <output.json>

**Public domain**: The KJV text is in the public domain.  The parser source
code and the generated JSON may be freely committed and distributed.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pypdf
from pydantic import ValidationError

from soap_journal.core.bible.books import ALL_BOOKS, get_book_by_name
from soap_journal.parsers.schema import (
    CanonicalBook,
    CanonicalChapter,
    CanonicalHeading,
    CanonicalTranslation,
    CanonicalVerse,
)

KJV_CODE = "KJV"
KJV_NAME = "King James Version"
KJV_LANGUAGE = "en"
KJV_COPYRIGHT = "The King James Version is in the public domain."

_CHAPTER_HEADER_RE = re.compile(r"^(.+)\s+(\d+)$")

_VERSE_SPLIT_RE = re.compile(
    r"(?:^|(?<=\s))(\d+)\s+(?=[A-Z‘“\[\(])"
)

_CROSS_REF_RE = re.compile(r"^\(.*\d+:\d+.*\)$")

_SAYING_RE = re.compile(r"^Saying\s+\d+$")

_FOOTER = "KJV  [Online]"

_TITLE_CASE_SMALL = frozenset(
    "a an the of in for and to is with by on at or nor but not".split()
)


class KjvParseError(Exception):
    """Raised for any structural problem in the KJV source."""


BooksData = dict[str, dict[int, list[tuple[int, str]]]]
HeadingsData = dict[str, dict[int, list[tuple[int, str]]]]


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
    """Normalise extracted PDF text into logical lines.

    The KJV PDF extraction produces verse numbers at the end of lines
    followed by U+202F (narrow no-break space) at the start of the next.
    This step:
    1. Replaces U+202F with regular space.
    2. Replaces form-feeds with newlines (page break = line break).
    3. Joins any line that starts with a space to the previous line,
       reconstituting inline verse markers.
    """
    text = text.replace(" ", " ").replace("\f", "\n")
    raw_lines = text.splitlines()
    merged: list[str] = []
    for line in raw_lines:
        if line.startswith(" ") and merged:
            merged[-1] = merged[-1] + line
        else:
            merged.append(line)
    return merged


def _try_chapter_header(line: str) -> tuple[str, int] | None:
    m = _CHAPTER_HEADER_RE.match(line)
    if m is None:
        return None
    book_part = m.group(1).strip()
    if get_book_by_name(book_part) is None:
        return None
    return book_part, int(m.group(2))


def _is_cross_reference(line: str) -> bool:
    return bool(_CROSS_REF_RE.match(line))


def _split_verses(line: str) -> list[tuple[int, str]] | None:
    """Split a line containing inline verse markers.

    Returns ``[(verse_number, text_fragment), ...]`` or ``None`` if the
    line has no verse markers.  A verse_number of ``0`` is a sentinel
    meaning "continuation text from the previous verse".
    """
    matches = list(_VERSE_SPLIT_RE.finditer(line))
    if not matches:
        return None

    result: list[tuple[int, str]] = []

    if matches[0].start() > 0:
        leading = line[: matches[0].start()].strip()
        if leading:
            result.append((0, leading))

    for i, m in enumerate(matches):
        verse_num = int(m.group(1))
        text_start = m.end()
        text_end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
        text = line[text_start:text_end].strip()
        if text:
            result.append((verse_num, text))

    return result if result else None


def _is_likely_heading(line: str, prev_text: str) -> bool:
    """Heuristic: section heading vs. verse continuation."""
    if not line or len(line) > 120:
        return False
    if line[0].islower():
        return False

    words = line.rstrip(".").split()
    if len(words) > 12:
        return False

    all_title = all(
        w[0].isupper() or w.lower() in _TITLE_CASE_SMALL for w in words if w
    )
    if not all_title:
        return False

    if prev_text and not prev_text.rstrip().endswith((".", "?", "!", ":")):
        return False

    return True


def parse_lines(text: str) -> tuple[BooksData, HeadingsData, list[str]]:
    """Line-level parse of preprocessed KJV text.

    Returns ``(books_data, headings_data, rename_notices)``.
    """
    lines = _preprocess(text)

    books_data: BooksData = {}
    headings_data: HeadingsData = {}
    rename_notices: list[str] = []
    seen_source_names: dict[str, str] = {}

    current_book: str | None = None
    current_chapter: int = 0
    current_verse: int = 0
    current_text: str = ""
    pending_headings: list[str] = []
    started: bool = False

    def _resolve_book(source_name: str) -> str:
        cached = seen_source_names.get(source_name)
        if cached is not None:
            return cached
        book = get_book_by_name(source_name)
        if book is None:
            raise KjvParseError(
                f"book {source_name!r} does not match any canonical name or alias"
            )
        seen_source_names[source_name] = book.name
        if source_name != book.name:
            rename_notices.append(f"{source_name} -> {book.name}")
        return book.name

    def _flush_verse() -> None:
        nonlocal current_verse, current_text
        if current_book is None or current_verse == 0:
            return
        trimmed = current_text.strip()
        if trimmed:
            chapter_verses = books_data[current_book][current_chapter]
            chapter_verses.append((current_verse, trimmed))
        current_verse = 0
        current_text = ""

    def _flush_headings(before_verse: int) -> None:
        if not pending_headings or current_book is None:
            return
        chapter_headings = headings_data[current_book][current_chapter]
        for h in pending_headings:
            chapter_headings.append((before_verse, h))
        pending_headings.clear()

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        # 1. Footer
        if line == _FOOTER:
            continue

        # 2. Cross-reference
        if _is_cross_reference(line):
            continue

        # 3. "Saying N" sub-section markers in Proverbs
        if _SAYING_RE.match(line):
            continue

        # 4. Chapter header
        header = _try_chapter_header(line)
        if header is not None:
            last_verse = current_verse
            _flush_verse()
            if pending_headings and last_verse > 0:
                _flush_headings(last_verse)
            source_name, chapter_num = header
            canonical = _resolve_book(source_name)
            current_book = canonical
            current_chapter = chapter_num
            current_verse = 0
            current_text = ""
            pending_headings.clear()
            books_data.setdefault(canonical, {}).setdefault(chapter_num, [])
            headings_data.setdefault(canonical, {}).setdefault(chapter_num, [])
            started = True
            continue

        if not started:
            continue

        # 6. Verse-bearing line
        splits = _split_verses(line)
        if splits is not None:
            for verse_num, fragment in splits:
                if verse_num == 0:
                    current_text += " " + fragment
                else:
                    _flush_verse()
                    _flush_headings(verse_num)
                    current_verse = verse_num
                    current_text = fragment
            continue

        # 7. Heading or continuation
        if current_verse == 0:
            pending_headings.append(line)
        elif _is_likely_heading(line, current_text):
            _flush_verse()
            pending_headings.append(line)
        else:
            current_text += " " + line

    _flush_verse()

    if not books_data:
        raise KjvParseError("no verse lines found")

    return books_data, headings_data, rename_notices


def build_canonical_translation(
    books_data: BooksData,
    headings_data: HeadingsData,
) -> CanonicalTranslation:
    """Assemble a validated CanonicalTranslation from parsed KJV data."""
    canonical_books: list[CanonicalBook] = []
    for spec in ALL_BOOKS:
        chapters_dict = books_data.get(spec.name)
        if not chapters_dict:
            raise KjvParseError(f"source is missing book {spec.name!r}")

        chapters_sorted: list[CanonicalChapter] = []
        for chapter_number in sorted(chapters_dict.keys()):
            verses = sorted(chapters_dict[chapter_number], key=lambda t: t[0])

            chapter_headings_raw = headings_data.get(spec.name, {}).get(
                chapter_number, []
            )
            headings = [
                CanonicalHeading(before_verse=bv, text=t)
                for bv, t in chapter_headings_raw
            ]

            chapters_sorted.append(
                CanonicalChapter(
                    number=chapter_number,
                    verses=[
                        CanonicalVerse(number=n, text=t) for n, t in verses
                    ],
                    headings=headings,
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
        code=KJV_CODE,
        name=KJV_NAME,
        language=KJV_LANGUAGE,
        copyright=KJV_COPYRIGHT,
        books=canonical_books,
    )


def parse_kjv_source(text: str) -> tuple[CanonicalTranslation, list[str]]:
    """Parse KJV text into a fully-validated CanonicalTranslation."""
    books_data, headings_data, renames = parse_lines(text)
    return build_canonical_translation(books_data, headings_data), renames


def _write_canonical_json(
    translation: CanonicalTranslation, out_path: Path
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        translation.model_dump_json(indent=2), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m soap_journal.parsers.kjv",
        description="Parse a KJV PDF into canonical Bible JSON.",
    )
    parser.add_argument("source", type=Path, help="Path to the KJV PDF")
    parser.add_argument(
        "--out", type=Path, required=True, help="Output path for canonical JSON"
    )
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
        translation, renames = parse_kjv_source(source_text)
    except KjvParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ValidationError as exc:
        print(
            f"error: canonical schema validation failed:\n{exc}",
            file=sys.stderr,
        )
        return 1

    _write_canonical_json(translation, args.out)
    for notice in renames:
        print(f"book rename: {notice}")
    chapters = sum(len(b.chapters) for b in translation.books)
    verses = sum(
        len(c.verses) for b in translation.books for c in b.chapters
    )
    print(
        f"Parsed {translation.code}: {len(translation.books)} books, "
        f"{chapters} chapters, {verses} verses -> {args.out}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - thin shell
    raise SystemExit(main())
