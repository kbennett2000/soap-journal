"""NKJV parser CLI.

Converts a user-provided New King James Version PDF into canonical Bible JSON.

Source format
-------------
- 908-page PDF with a single embedded TrueType font.
- Page 1 has two title lines ("The Holy Bible" / "New King James Version
  1982 NKJV") that are skipped automatically.
- Each verse occupies one logical line: ``<Abbr> <Chapter>:<Verse> <Text>``.
- Long verses wrap to continuation lines that have NO verse prefix.
  The parser joins these into the verse they belong to.
- Form-feed page breaks may appear between pages; verses can wrap across
  them.  Treat form-feeds as whitespace.
- Bracketed italics like ``[was]``, ``[is]`` represent translator additions
  printed in italics.  Preserved verbatim.
- 66 books, 31,102 verses.
- No section headings, footnotes, or red-letter formatting in the source.

Usage
-----
    python -m soap_journal.parsers.nkjv <source.pdf> --out <output.json>

Exits non-zero with a useful message on:
- Unreadable source PDF.
- A book abbreviation that doesn't match any canonical name or alias.
- A line that doesn't parse as a verse or continuation.
- Canonical-schema validation failure.

**Copyright notice**: The NKJV text is copyrighted by Thomas Nelson (1982).
The *parser source code* is MIT-licensed and committed to the repo.
The PDF and generated JSON must NOT be committed.
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
    CanonicalTranslation,
    CanonicalVerse,
)

NKJV_CODE = "NKJV"
NKJV_NAME = "New King James Version"
NKJV_LANGUAGE = "en"
NKJV_COPYRIGHT = (
    "Scripture taken from the New King James Version®. "
    "Copyright © 1982 by Thomas Nelson. "
    "Used by permission. All rights reserved."
)

# Matches a verse-opening line: <Abbr> <chapter>:<verse> <text>
# The abbreviation is an optional leading digit (1-3) followed by 2-3 letters.
_VERSE_RE = re.compile(r"^([1-3]?[A-Za-z]{2,3})\s+(\d+):(\d+)\s+(.+)$")


class NkjvParseError(Exception):
    """Raised for any structural problem in the NKJV source."""


# Intermediate dict the line parser produces.
# canonical_book_name -> {chapter_number: [(verse_number, text), ...]}
BooksData = dict[str, dict[int, list[tuple[int, str]]]]


def _read_pdf(path: Path) -> str:
    """Extract text from every page of a PDF, joined with form-feeds."""
    reader = pypdf.PdfReader(path)
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\f".join(pages)


def parse_lines(text: str) -> tuple[BooksData, list[str]]:
    """Line-level parse of NKJV-formatted text with continuation-line joining.

    Returns ``(books_data, rename_notices)``.  Does NOT validate that every
    canonical book is present — that's ``build_canonical_translation``'s job.
    """
    books_data: BooksData = {}
    rename_notices: list[str] = []
    seen_source_names: dict[str, str] = {}

    current_abbr: str | None = None
    current_chapter: int = 0
    current_verse: int = 0
    current_text: str = ""
    current_lineno: int = 0

    def _flush() -> None:
        nonlocal current_abbr
        if current_abbr is None:
            return

        canonical_name = seen_source_names.get(current_abbr)
        if canonical_name is None:
            book = get_book_by_name(current_abbr)
            if book is None:
                raise NkjvParseError(
                    f"line {current_lineno}: book {current_abbr!r} does not "
                    f"match any canonical name or alias"
                )
            canonical_name = book.name
            seen_source_names[current_abbr] = canonical_name
            if current_abbr != canonical_name:
                rename_notices.append(f"{current_abbr} -> {canonical_name}")

        chapter_verses = books_data.setdefault(canonical_name, {}).setdefault(current_chapter, [])
        chapter_verses.append((current_verse, current_text.strip()))
        current_abbr = None

    lines = text.splitlines()

    for lineno, raw in enumerate(lines, start=1):
        # Strip form-feed characters (page breaks).
        line = raw.replace("\f", "").strip()
        if not line:
            continue

        match = _VERSE_RE.match(line)
        if match:
            _flush()
            current_abbr = match.group(1)
            current_chapter = int(match.group(2))
            current_verse = int(match.group(3))
            current_text = match.group(4)
            current_lineno = lineno
        elif current_abbr is not None:
            # Continuation line: append to current verse.
            current_text += " " + line
        # else: title / header line before the first verse — skip.

    _flush()

    if not books_data:
        raise NkjvParseError("no verse lines found")

    return books_data, rename_notices


def build_canonical_translation(books_data: BooksData) -> CanonicalTranslation:
    """Assemble a validated CanonicalTranslation from parsed NKJV books data."""
    canonical_books: list[CanonicalBook] = []
    for spec in ALL_BOOKS:
        chapters_dict = books_data.get(spec.name)
        if not chapters_dict:
            raise NkjvParseError(f"source is missing book {spec.name!r}")

        chapters_sorted: list[CanonicalChapter] = []
        for chapter_number in sorted(chapters_dict.keys()):
            verses = sorted(chapters_dict[chapter_number], key=lambda t: t[0])
            chapters_sorted.append(
                CanonicalChapter(
                    number=chapter_number,
                    verses=[CanonicalVerse(number=n, text=t) for n, t in verses],
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
        code=NKJV_CODE,
        name=NKJV_NAME,
        language=NKJV_LANGUAGE,
        copyright=NKJV_COPYRIGHT,
        books=canonical_books,
    )


def parse_nkjv_source(text: str) -> tuple[CanonicalTranslation, list[str]]:
    """Parse NKJV text into a fully-validated CanonicalTranslation."""
    books_data, renames = parse_lines(text)
    return build_canonical_translation(books_data), renames


def _write_canonical_json(translation: CanonicalTranslation, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(translation.model_dump_json(indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m soap_journal.parsers.nkjv",
        description="Parse an NKJV PDF into canonical Bible JSON.",
    )
    parser.add_argument("source", type=Path, help="Path to the NKJV PDF")
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
        translation, renames = parse_nkjv_source(source_text)
    except NkjvParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ValidationError as exc:
        print(f"error: canonical schema validation failed:\n{exc}", file=sys.stderr)
        return 1

    _write_canonical_json(translation, args.out)
    for notice in renames:
        print(f"book rename: {notice}")
    chapters = sum(len(b.chapters) for b in translation.books)
    verses = sum(len(c.verses) for b in translation.books for c in b.chapters)
    print(
        f"Parsed {translation.code}: {len(translation.books)} books, "
        f"{chapters} chapters, {verses} verses -> {args.out}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - thin shell
    raise SystemExit(main())
