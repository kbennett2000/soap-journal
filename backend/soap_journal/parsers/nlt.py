"""NLT parser CLI.

Converts a user-provided New Living Translation PDF into canonical
Bible JSON.

Source format
-------------
- 1,798-page two-column PDF (432x576pt tablet format).
- Book headers are standalone lines matching canonical book names or
  NLT-specific ordinal variants (``1st Samuel``, ``2nd Kings``, etc.).
- Chapter and verse markers both use the **inline** format:
  ``<N><Capital-or-Quote>...`` with no space between the number and the
  text.  Examples: ``1In the beginning God created the``,
  ``2The earth was empty``, ``6"Now you will see``.
  The distinction between a chapter marker and a verse marker is
  **sequential context**: if N equals current_verse + 1, it is the
  next verse; otherwise it starts a new chapter (chapter N, verse 1).
- **Psalms exception**: each psalm begins with a ``PSALM <N>`` header
  on its own line, followed by inline verse markers.
- No section headings, footnotes, or red-letter in this PDF rendering.
- Form-feed page breaks treated as whitespace.
- Watermark lines (``Search Biiible``) filtered.
- 66 books, 1,189 chapters.

Usage
-----
    python -m soap_journal.parsers.nlt <source.pdf> --out <output.json>

**Prerequisite**: ``pdftotext`` from poppler-utils must be on ``PATH``.

**Copyright**: The NLT text is copyrighted by Tyndale House Foundation.
The parser source code is MIT-licensed.  The PDF and generated JSON
must NOT be committed.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from pydantic import ValidationError

from soap_journal.core.bible.books import ALL_BOOKS, get_book_by_name
from soap_journal.parsers.schema import (
    CanonicalBook,
    CanonicalChapter,
    CanonicalTranslation,
    CanonicalVerse,
)

NLT_CODE = "NLT"
NLT_NAME = "New Living Translation"
NLT_LANGUAGE = "en"
NLT_COPYRIGHT = (
    "Holy Bible, New Living Translation, copyright © 1996, 2004, 2015 "
    "by Tyndale House Foundation. Used by permission of Tyndale House "
    "Publishers, Carol Stream, Illinois 60188. All rights reserved."
)

# Inline numbered marker: digits immediately followed by a letter,
# quote, or opening paren, no space.  Used for BOTH chapter and verse
# markers; the parser distinguishes them by sequential context.
_NUMBERED_LINE_RE = re.compile(r"^(\d+)([\"'(a-zA-Z].*)$")

# Guards against false-positive numbered-line matches.
_ORDINAL_PREFIX_RE = re.compile(r"^\d+(st|nd|rd|th)\s")
_FRACTION_RE = re.compile(r"^\d+/")
_COMMA_NUMBER_RE = re.compile(r"^\d+,")

# Psalm chapter header (Psalms only).
_PSALM_HEADER_RE = re.compile(r"^PSALM\s+(\d+)$")

_WATERMARKS = frozenset({"Search Biiible", "Search Biiible.com"})

# Expected chapter count per book — fixed across all Protestant translations.
# Used to disambiguate inline numbered markers: a number exceeding the
# book's chapter count cannot be a chapter start.
_EXPECTED_CHAPTERS: dict[str, int] = {
    "Genesis": 50, "Exodus": 40, "Leviticus": 27, "Numbers": 36,
    "Deuteronomy": 34, "Joshua": 24, "Judges": 21, "Ruth": 4,
    "1 Samuel": 31, "2 Samuel": 24, "1 Kings": 22, "2 Kings": 25,
    "1 Chronicles": 29, "2 Chronicles": 36, "Ezra": 10, "Nehemiah": 13,
    "Esther": 10, "Job": 42, "Psalms": 150, "Proverbs": 31,
    "Ecclesiastes": 12, "Song of Solomon": 8, "Isaiah": 66, "Jeremiah": 52,
    "Lamentations": 5, "Ezekiel": 48, "Daniel": 12, "Hosea": 14,
    "Joel": 3, "Amos": 9, "Obadiah": 1, "Jonah": 4,
    "Micah": 7, "Nahum": 3, "Habakkuk": 3, "Zephaniah": 3,
    "Haggai": 2, "Zechariah": 14, "Malachi": 4,
    "Matthew": 28, "Mark": 16, "Luke": 24, "John": 21,
    "Acts": 28, "Romans": 16, "1 Corinthians": 16, "2 Corinthians": 13,
    "Galatians": 6, "Ephesians": 6, "Philippians": 4, "Colossians": 4,
    "1 Thessalonians": 5, "2 Thessalonians": 3, "1 Timothy": 6, "2 Timothy": 4,
    "Titus": 3, "Philemon": 1, "Hebrews": 13, "James": 5,
    "1 Peter": 5, "2 Peter": 3, "1 John": 5, "2 John": 1,
    "3 John": 1, "Jude": 1, "Revelation": 22,
}


class NltParseError(Exception):
    """Raised for any structural problem in the NLT source."""


BooksData = dict[str, dict[int, list[tuple[int, str]]]]


def _read_pdf(path: Path) -> str:
    """Extract text from a two-column PDF using ``pdftotext -raw``.

    The NLT PDF renders two columns per page.  ``pypdf`` reads across
    both columns (row-first), interleaving verses from left and right.
    ``pdftotext -raw`` walks column-first, preserving correct order.
    """
    try:
        result = subprocess.run(
            ["pdftotext", "-raw", str(path), "-"],
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
    except subprocess.TimeoutExpired as exc:
        raise OSError("pdftotext timed out after 300 seconds") from exc
    if result.returncode != 0:
        raise OSError(
            f"pdftotext failed (exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )
    return result.stdout


def _preprocess(text: str) -> list[str]:
    """Normalize extracted text into logical lines.

    Different ``pdftotext`` builds format verse numbers differently:
    Xpdf emits them inline with the verse text (``30And I have given``),
    while poppler emits the number on its own line followed by the text.
    Chapter markers are inline in both.  This step normalizes poppler's
    standalone verse numbers into the inline form by merging a numeric
    line into the following line — but only when that line begins with
    non-digit text.  A standalone number followed by another number is a
    census/count figure inside verse text (e.g. Ezra 2), not a verse
    marker, so it is left alone to become continuation text.
    """
    lines = [
        line
        for line in (raw.strip() for raw in text.replace("\f", "\n").splitlines())
        if line and line not in _WATERMARKS
    ]
    merged: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if (
            line.isdigit()
            and i + 1 < len(lines)
            and not lines[i + 1][0].isdigit()
        ):
            merged.append(line + lines[i + 1])
            i += 2
        else:
            merged.append(line)
            i += 1
    return merged


def _try_book_name(line: str) -> str | None:
    """Return canonical book name if *line* is a book header, else None."""
    book = get_book_by_name(line)
    return book.name if book is not None else None


def _parse_numbered_line(line: str) -> tuple[int, str] | None:
    """Parse an inline numbered marker (``N<Capital-or-Quote>...``).

    Returns ``(number, text)`` or ``None``.  Guards against ordinal
    book names, fractions, and comma-separated numbers.
    """
    if _ORDINAL_PREFIX_RE.match(line):
        return None
    if _FRACTION_RE.match(line):
        return None
    if _COMMA_NUMBER_RE.match(line):
        return None

    m = _NUMBERED_LINE_RE.match(line)
    if m is None:
        return None

    return int(m.group(1)), m.group(2)


def parse_lines(text: str) -> tuple[BooksData, list[str]]:
    """Parse preprocessed NLT text into intermediate data structures.

    Both chapter and verse markers use the same inline format
    (``N<letter/quote>...``).  The parser distinguishes them by
    sequential context plus a **lookahead** to resolve ambiguity
    when a number could be either the next verse or a new chapter.

    Returns ``(books_data, rename_notices)``.
    """
    lines = _preprocess(text)

    books_data: BooksData = {}
    rename_notices: list[str] = []
    seen_source_names: dict[str, str] = {}

    current_book: str | None = None
    current_chapter: int = 0
    current_verse: int = 0
    current_text_parts: list[str] = []
    started: bool = False

    def _resolve_book(source_name: str) -> str:
        cached = seen_source_names.get(source_name)
        if cached is not None:
            return cached
        book = get_book_by_name(source_name)
        if book is None:
            raise NltParseError(
                f"book {source_name!r} does not match any canonical name or alias"
            )
        canonical = book.name
        seen_source_names[source_name] = canonical
        if source_name != canonical:
            rename_notices.append(f"{source_name} -> {canonical}")
        return canonical

    def _flush_verse() -> None:
        nonlocal current_verse
        if current_book is None or current_verse == 0:
            return
        assembled = " ".join(current_text_parts).strip()
        if not assembled:
            return
        chapter_verses = books_data[current_book][current_chapter]
        chapter_verses.append((current_verse, assembled))
        current_verse = 0
        current_text_parts.clear()

    def _start_chapter(chapter_num: int) -> None:
        nonlocal current_chapter, current_verse
        current_chapter = chapter_num
        current_verse = 0
        current_text_parts.clear()
        books_data.setdefault(current_book, {}).setdefault(chapter_num, [])  # type: ignore[arg-type]

    def _peek_next_numbered(start: int) -> tuple[int, int] | None:
        """Find the next numbered line after index *start*.

        Returns ``(number, line_index)`` or ``None``.  Stops at
        book headers and PSALM headers to avoid crossing boundaries.
        """
        for j in range(start + 1, min(start + 50, len(lines))):
            p = _parse_numbered_line(lines[j])
            if p is not None:
                return p[0], j
            if current_book == "Psalms" and _PSALM_HEADER_RE.match(lines[j]):
                return None
            if _try_book_name(lines[j]) is not None:
                return None
        return None

    def _is_chapter_start(number: int, line_idx: int) -> bool:
        """Decide if numbered line *number* starts a new chapter.

        Uses ``current_chapter + 1`` as the expected next chapter,
        the book's total chapter count, and a lookahead to resolve
        the ambiguous case where the number is both the next verse
        AND the expected next chapter.
        """
        if current_chapter == 0:
            return True

        max_ch = _EXPECTED_CHAPTERS.get(current_book, 0)  # type: ignore[arg-type]
        next_ch = current_chapter + 1

        if number == current_verse + 1:
            # Sequential — default to verse unless it is also the
            # expected next chapter.
            if number != next_ch or number > max_ch:
                return False
            # Ambiguous: number is both next verse AND next chapter.
            # Lookahead: if the following numbered line continues the
            # sequence (number + 1), this is a verse.  If it equals 2
            # (verse 2 of a new chapter), this is a chapter start.
            first = _peek_next_numbered(line_idx)
            if first is None:
                return False
            n1, _ = first
            if n1 == number + 1:
                return False
            return n1 == 2

        # Non-sequential.
        if number == next_ch and number <= max_ch:
            return True  # Expected next chapter.
        return False  # Verse gap or stray number.

    i = 0
    while i < len(lines):
        line = lines[i]

        # 1. Book header with lookahead to distinguish body from TOC.
        book_name = _try_book_name(line)
        if book_name is not None:
            j = i + 1
            if j < len(lines):
                next_line = lines[j]
                is_chapter = False
                if book_name == "Psalms":
                    is_chapter = _PSALM_HEADER_RE.match(next_line) is not None
                else:
                    is_chapter = _parse_numbered_line(next_line) is not None
                if is_chapter:
                    _flush_verse()
                    canonical = _resolve_book(line)
                    current_book = canonical
                    current_chapter = 0
                    current_verse = 0
                    current_text_parts.clear()
                    started = True
                    i += 1
                    continue
            # TOC entry or unrecognized context — skip.
            i += 1
            continue

        if not started:
            i += 1
            continue

        # 2. PSALM N header (Psalms only).
        if current_book == "Psalms":
            m = _PSALM_HEADER_RE.match(line)
            if m:
                _flush_verse()
                _start_chapter(int(m.group(1)))
                i += 1
                continue

        # 3. Inline numbered marker — chapter or verse, distinguished
        #    by sequential context with lookahead disambiguation.
        parsed = _parse_numbered_line(line)
        if parsed is not None:
            number, text = parsed
            if _is_chapter_start(number, i):
                _flush_verse()
                _start_chapter(number)
                current_verse = 1
                current_text_parts = [text]
            else:
                _flush_verse()
                current_verse = number
                current_text_parts = [text]
            i += 1
            continue

        # 4. Verse continuation text.
        if current_verse > 0:
            current_text_parts.append(line)

        i += 1

    _flush_verse()

    if not books_data:
        raise NltParseError("no verse lines found")

    return books_data, rename_notices


def _split_merged_chapters(books_data: BooksData) -> None:
    """Detect and split chapters that were merged due to missing markers.

    When the NLT PDF omits a chapter marker (e.g. Daniel 11:1 folded
    into 10:21), the parser produces one oversized chapter.  This
    function detects verse-number resets within a chapter and splits
    at each reset, assigning sequential chapter numbers.

    After splitting, single-entry segments whose only verse number
    equals the assigned chapter number are merged into the following
    segment (the entry is the chapter marker containing verse 1).
    """
    for book_name in list(books_data):
        max_ch = _EXPECTED_CHAPTERS.get(book_name, 0)
        actual_chs = len(books_data[book_name])
        if actual_chs >= max_ch:
            continue

        for ch_num in sorted(books_data[book_name]):
            verses = books_data[book_name][ch_num]
            v_nums = [v[0] for v in verses]

            splits: list[int] = []
            for idx in range(1, len(v_nums)):
                if v_nums[idx] < v_nums[idx - 1] and (v_nums[idx - 1] - v_nums[idx]) > 5:
                    splits.append(idx)

            if not splits:
                continue

            segments: list[list[tuple[int, str]]] = []
            prev = 0
            for s in splits:
                segments.append(verses[prev:s])
                prev = s
            segments.append(verses[prev:])

            # Merge single-entry segments that are chapter markers
            # into the following segment.
            merged: list[list[tuple[int, str]]] = []
            i = 0
            while i < len(segments):
                seg = segments[i]
                if (
                    len(seg) == 1
                    and i + 1 < len(segments)
                    and segments[i + 1]
                    and segments[i + 1][0][0] < seg[0][0]
                ):
                    merged.append(seg + segments[i + 1])
                    i += 2
                else:
                    merged.append(seg)
                    i += 1

            books_data[book_name][ch_num] = merged[0]
            next_ch = ch_num + 1
            for seg in merged[1:]:
                if next_ch <= max_ch and next_ch not in books_data[book_name]:
                    books_data[book_name][next_ch] = seg
                    next_ch += 1


def build_canonical_translation(books_data: BooksData) -> CanonicalTranslation:
    """Assemble a validated CanonicalTranslation from parsed NLT data.

    The NLT omits certain disputed verses (e.g. Acts 8:37, John 5:4).
    Missing verse numbers are filled with placeholder text so the
    canonical schema's 1..N invariant holds and verse numbers stay
    aligned with other translations.
    """
    canonical_books: list[CanonicalBook] = []
    for spec in ALL_BOOKS:
        chapters_dict = books_data.get(spec.name)
        if not chapters_dict:
            raise NltParseError(f"source is missing book {spec.name!r}")

        chapters_sorted: list[CanonicalChapter] = []
        for chapter_number in sorted(chapters_dict.keys()):
            raw = sorted(chapters_dict[chapter_number], key=lambda t: t[0])
            if not raw:
                continue
            max_v = raw[-1][0]
            verse_map = dict(raw)
            canon_verses: list[CanonicalVerse] = []
            for v in range(1, max_v + 1):
                text = verse_map.get(v)
                if text is None:
                    text = "[verse not included in the NLT]"
                canon_verses.append(CanonicalVerse(number=v, text=text))
            chapters_sorted.append(
                CanonicalChapter(
                    number=chapter_number,
                    verses=canon_verses,
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
        code=NLT_CODE,
        name=NLT_NAME,
        language=NLT_LANGUAGE,
        copyright=NLT_COPYRIGHT,
        books=canonical_books,
    )


def parse_nlt_source(text: str) -> tuple[CanonicalTranslation, list[str]]:
    """Parse NLT text into a fully-validated CanonicalTranslation."""
    books_data, renames = parse_lines(text)
    _split_merged_chapters(books_data)
    return build_canonical_translation(books_data), renames


def _write_canonical_json(
    translation: CanonicalTranslation, out_path: Path
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        translation.model_dump_json(indent=2), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m soap_journal.parsers.nlt",
        description="Parse an NLT PDF into canonical Bible JSON.",
    )
    parser.add_argument("source", type=Path, help="Path to the NLT PDF")
    parser.add_argument(
        "--out", type=Path, required=True, help="Output path for canonical JSON"
    )
    args = parser.parse_args(argv)

    try:
        source_text = _read_pdf(args.source)
    except FileNotFoundError:
        print(
            "error: pdftotext not found; install poppler-utils",
            file=sys.stderr,
        )
        return 2
    except OSError as exc:
        print(f"error: cannot read source: {exc}", file=sys.stderr)
        return 2

    try:
        translation, renames = parse_nlt_source(source_text)
    except NltParseError as exc:
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
