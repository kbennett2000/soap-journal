"""Verse reference parser.

Turns user-typed strings like ``"John 3:16-20"`` into a structured, validated
``ParsedReference``. The single source of truth for what reference syntax the
app accepts — both the jump bar's `/bible/resolve` endpoint and any future
caller should funnel through ``parse_reference``.

This module does not touch the database. It validates structure against the
static book list in :mod:`soap_journal.core.bible.books`. Whether the
chapter/verse range actually exists in a loaded translation is the API
layer's job (it has the DB session).

Accepted syntax (v1)
--------------------
- ``"John 3:16"``                 single verse
- ``"John 3:16-20"``              verse range within one chapter
- ``"John 3"``                    whole chapter (no verse component)
- Abbreviations / aliases:        ``"Jn 3:16"``, ``"1Cor 13"``, ``"Apocalypse 22:21"``
- Case-insensitive, whitespace-tolerant, en/em dash as range separator,
  no-space numbered books (``"1John 3:16"``).

Rejected (v1)
-------------
- Empty input, book name alone, unknown book.
- Cross-chapter ranges (``"John 3:30-4:2"``). Documented as a v2 deferral.
- Multiple references separated by ``;`` or ``,``. One reference per call.
- Reversed range, non-positive numbers, partial garbage.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from soap_journal.core.bible.books import Book, get_book_by_name


class ReferenceParseError(ValueError):
    """Raised when the input string cannot be turned into a ParsedReference.

    The API layer maps this to ``400 INVALID_REFERENCE`` and surfaces
    ``str(exc)`` as the user-facing message.
    """


class ParsedReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    book: Book
    chapter: int
    start_verse: int | None
    end_verse: int | None
    canonical_string: str


# Normalize en/em dashes to ASCII hyphen before matching so the regex only
# has to think about one separator.
_DASH_CHARS = ("–", "—", "−")  # en, em, minus sign


# Single regex with named groups. Book is constrained to "[optional 1-3
# numbered prefix] + alphabetic word(s)" so backtracking can't smuggle
# digits or dashes into the book name (which would turn "John 3:30-4:2"
# into a fake book like "John 3:30-"). Verse / range are optional.
_REF_RE = re.compile(
    r"""
    ^
    (?P<book>
        (?:[1-3]\s*)?                # optional leading 1/2/3 (numbered books)
        [A-Za-z]+                    # first alphabetic word
        (?:\s+[A-Za-z]+)*            # additional whitespace-separated words
    )
    \s+
    (?P<chapter>\d+)                 # chapter number
    (?:                              # optional ":verse(-end)?" group
        \s*:\s*
        (?P<start_verse>\d+)
        (?:
            \s*-\s*
            (?P<end_verse>\d+)
        )?
    )?
    $
    """,
    re.VERBOSE,
)


def _looks_like_multi_reference(s: str) -> bool:
    """Reject inputs that try to pack more than one reference per call."""
    return ";" in s or "," in s


def _normalize(raw: str) -> str:
    """Lowercase dashes, collapse whitespace runs to single spaces, strip ends."""
    s = raw
    for dash in _DASH_CHARS:
        s = s.replace(dash, "-")
    # Collapse any whitespace run to a single space; the regex tolerates a
    # single optional space at each boundary.
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _canonical_string(
    book: Book, chapter: int, start: int | None, end: int | None
) -> str:
    if start is None:
        return f"{book.name} {chapter}"
    if end is None or end == start:
        return f"{book.name} {chapter}:{start}"
    return f"{book.name} {chapter}:{start}-{end}"


def parse_reference(raw: str) -> ParsedReference:
    """Parse a user-typed reference string. Raises ``ReferenceParseError`` on failure."""
    if not raw or not raw.strip():
        raise ReferenceParseError("reference is empty")

    if _looks_like_multi_reference(raw):
        raise ReferenceParseError(
            "multiple references are not supported; provide one reference per call"
        )

    s = _normalize(raw)
    match = _REF_RE.match(s)
    if match is None:
        # Did the user type just a known book name without a chapter? Give
        # a specific message; otherwise the input is opaque garbage.
        if get_book_by_name(s) is not None:
            raise ReferenceParseError(
                f"reference is missing a chapter number: {raw!r}"
            )
        raise ReferenceParseError(f"could not parse reference: {raw!r}")

    book_str = match.group("book").strip()
    chapter = int(match.group("chapter"))
    start_str = match.group("start_verse")
    end_str = match.group("end_verse")

    book = get_book_by_name(book_str)
    if book is None:
        raise ReferenceParseError(f"unknown book: {book_str!r}")

    if chapter < 1:
        raise ReferenceParseError(f"chapter must be 1 or greater, got {chapter}")

    if start_str is None:
        # Whole-chapter reference. There's no syntactic way to write
        # "John 3-4" today; cross-chapter ranges are deferred.
        return ParsedReference(
            book=book,
            chapter=chapter,
            start_verse=None,
            end_verse=None,
            canonical_string=_canonical_string(book, chapter, None, None),
        )

    start_verse = int(start_str)
    if start_verse < 1:
        raise ReferenceParseError(
            f"verse must be 1 or greater, got {start_verse}"
        )

    if end_str is None:
        return ParsedReference(
            book=book,
            chapter=chapter,
            start_verse=start_verse,
            end_verse=start_verse,
            canonical_string=_canonical_string(book, chapter, start_verse, None),
        )

    # Cross-chapter ranges arrive only via ":start-chap:end" shapes — which
    # the regex doesn't match — but also via inputs the regex *did* accept.
    # In v1 the regex can't match "John 3:30-4:2" (no ":" allowed after
    # the dash), so its rejection happens here at the matcher level. If a
    # user feeds something that survives the regex but spans chapters,
    # we'd surface that as a "cross-chapter ranges not supported" message
    # — see the test for the explicit cross-chapter input.
    end_verse = int(end_str)
    if end_verse < 1:
        raise ReferenceParseError(f"verse must be 1 or greater, got {end_verse}")
    if end_verse < start_verse:
        raise ReferenceParseError(
            f"end verse must be >= start verse, got {start_verse}-{end_verse}"
        )

    return ParsedReference(
        book=book,
        chapter=chapter,
        start_verse=start_verse,
        end_verse=end_verse,
        canonical_string=_canonical_string(book, chapter, start_verse, end_verse),
    )


def _is_cross_chapter_attempt(raw: str) -> bool:
    """Detect ``"John 3:30-4:2"``-style inputs after normalization.

    These won't survive the main regex; we want to give a specific error
    rather than the generic "could not parse" message.
    """
    s = _normalize(raw)
    return bool(re.search(r"\d+:\d+\s*-\s*\d+:\d+", s))


def parse_reference_or_raise(raw: str) -> ParsedReference:
    """Same as ``parse_reference`` but with the cross-chapter case promoted to a
    dedicated error message so the API surfaces "not supported" instead of
    "could not parse". This is the function the API layer should call.
    """
    if _is_cross_chapter_attempt(raw):
        raise ReferenceParseError(
            "cross-chapter ranges are not supported in v1; "
            "use a single chapter (e.g. 'John 3:30-36')"
        )
    return parse_reference(raw)
