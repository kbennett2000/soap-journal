"""BSB parser CLI.

Converts the official tab-separated Berean Standard Bible plain-text source
(https://bereanbible.com/bsb.txt) into canonical Bible JSON.

Source format
-------------
- UTF-8 with a leading BOM.
- First three lines are header/license metadata (attribution + license
  notice + the literal "Verse\\t<translation name>" column header).
- Each subsequent line is `<Book Chapter:Verse>\\t<text>`.

The BSB has no headings, footnotes, or red-letter annotations in plain
text, so the canonical output's `headings` and `footnotes` lists stay
empty and every verse's `is_red_letter` is false.

Usage
-----
    python -m soap_journal.parsers.bsb <source.txt> --out <output.json>

Exits non-zero with a useful message on:
- Unreadable source.
- A book name that doesn't match any canonical name or alias.
- A line that doesn't parse as `Book Chapter:Verse\\tText`.
- Canonical-schema validation failure (gap in verses, missing book, etc.).
"""

from __future__ import annotations

import argparse
import re
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

BSB_CODE = "BSB"
BSB_NAME = "Berean Standard Bible"
BSB_LANGUAGE = "en"
BSB_COPYRIGHT = (
    "The Holy Bible, Berean Standard Bible, BSB is produced in cooperation "
    "with Bible Hub, Discovery Bible, unfoldingWord, Bible Aquifer, "
    "OpenBible.com, and the Berean Bible Translation Committee. "
    "This text of God's Word has been dedicated to the public domain. "
    "Free resources and databases are available at https://bereanbible.com/."
)

# A handful of verse references (Matthew 17:21, Mark 7:16, John 5:4, Acts
# 8:37, Romans 16:24, etc.) appear in the BSB source with empty text. These
# are the verses absent from the modern critical text but retained in older
# manuscript traditions; the BSB chooses not to translate them but keeps
# the numbering hole visible. To preserve the chapter's 1..N invariant we
# emit a recognizable placeholder. Anyone displaying the text can detect
# this exact string and render the BSB's editorial note.
OMITTED_VERSE_PLACEHOLDER = "[Verse omitted in earliest manuscripts.]"

# `<Book name> <chapter>:<verse>` where the book name may include digits and
# spaces (e.g. "1 Corinthians"). Greedy match on the book, anchored by the
# trailing " <chapter>:<verse>" pattern.
_REF_RE = re.compile(r"^(?P<book>.+?)\s+(?P<chapter>\d+):(?P<verse>\d+)$")


class BsbParseError(Exception):
    """Raised for any structural problem in the BSB source."""


# Type alias for the intermediate dict the line parser produces.
# canonical_book_name -> {chapter_number: [(verse_number, text), ...]}
BooksData = dict[str, dict[int, list[tuple[int, str]]]]


def parse_lines(text: str) -> tuple[BooksData, list[str]]:
    """Line-level parse of BSB plain text.

    Returns `(books_data, rename_notices)`. Does NOT validate that every
    canonical book is present — that's `build_canonical_translation`'s job.
    Exposed so tests can exercise the line parser with a fixture that only
    covers a couple of books.
    """
    lines = text.splitlines()
    # Strip leading BOM if present.
    if lines and lines[0].startswith("﻿"):
        lines[0] = lines[0].lstrip("﻿")

    # Skip header lines: BSB has 3, but the *exact* boundary is when we hit
    # a line whose first tab-separated cell parses as a reference. Detect
    # rather than assume to be robust to a future header change.
    data_start = None
    for idx, line in enumerate(lines):
        if "\t" not in line:
            continue
        ref = line.split("\t", 1)[0].strip()
        if _REF_RE.match(ref):
            data_start = idx
            break
    if data_start is None:
        raise BsbParseError("no verse lines found")

    rename_notices: list[str] = []
    seen_source_names: dict[str, str] = {}  # source name -> canonical name
    books_data: BooksData = {}

    for lineno, raw in enumerate(lines[data_start:], start=data_start + 1):
        if not raw.strip():
            continue
        if "\t" not in raw:
            raise BsbParseError(
                f"line {lineno}: expected tab-separated reference and text, got {raw!r}"
            )
        ref_str, _, verse_text = raw.partition("\t")
        ref_str = ref_str.strip()
        verse_text = verse_text.strip()
        if not verse_text:
            # See OMITTED_VERSE_PLACEHOLDER docstring: a small set of verses
            # are intentionally blank in the BSB source. Preserve the slot
            # so chapter numbering stays contiguous.
            verse_text = OMITTED_VERSE_PLACEHOLDER

        match = _REF_RE.match(ref_str)
        if match is None:
            raise BsbParseError(f"line {lineno}: cannot parse reference {ref_str!r}")
        source_book = match.group("book").strip()
        chapter = int(match.group("chapter"))
        verse = int(match.group("verse"))

        canonical_name = seen_source_names.get(source_book)
        if canonical_name is None:
            book = get_book_by_name(source_book)
            if book is None:
                raise BsbParseError(
                    f"line {lineno}: book {source_book!r} does not match "
                    f"any canonical name or alias"
                )
            canonical_name = book.name
            seen_source_names[source_book] = canonical_name
            if source_book != canonical_name:
                rename_notices.append(f"{source_book} -> {canonical_name}")

        chapter_verses = books_data.setdefault(canonical_name, {}).setdefault(chapter, [])
        chapter_verses.append((verse, verse_text))

    return books_data, rename_notices


def build_canonical_translation(books_data: BooksData) -> CanonicalTranslation:
    """Assemble a validated CanonicalTranslation from parsed BSB books data.

    Requires every canonical book to be present (this is where the
    "is BSB really 66 books?" check happens).
    """
    canonical_books: list[CanonicalBook] = []
    for spec in ALL_BOOKS:
        chapters_dict = books_data.get(spec.name)
        if not chapters_dict:
            raise BsbParseError(f"source is missing book {spec.name!r}")

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
        code=BSB_CODE,
        name=BSB_NAME,
        language=BSB_LANGUAGE,
        copyright=BSB_COPYRIGHT,
        books=canonical_books,
    )


def parse_bsb_source(text: str) -> tuple[CanonicalTranslation, list[str]]:
    """Parse BSB plain text into a fully-validated CanonicalTranslation.

    Returns the translation plus a list of human-readable rename notices
    ("Psalm -> Psalms"). Callers (the CLI, tests) print these.
    """
    books_data, renames = parse_lines(text)
    return build_canonical_translation(books_data), renames


def _read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_canonical_json(translation: CanonicalTranslation, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(translation.model_dump_json(indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m soap_journal.parsers.bsb",
        description="Parse the BSB plain-text source into canonical Bible JSON.",
    )
    parser.add_argument("source", type=Path, help="Path to bsb.txt")
    parser.add_argument("--out", type=Path, required=True, help="Output path for canonical JSON")
    args = parser.parse_args(argv)

    try:
        source_text = _read_source(args.source)
    except OSError as exc:
        print(f"error: cannot read source: {exc}", file=sys.stderr)
        return 2

    try:
        translation, renames = parse_bsb_source(source_text)
    except BsbParseError as exc:
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
