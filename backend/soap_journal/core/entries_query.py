"""Shared filter machinery for the entry list endpoint.

Defined as a small ``EntryFilters`` value object plus an ``apply_filters``
helper that adds WHERE clauses to both the count and page selects. Filters
that need related rows (book, tag) use correlated EXISTS subqueries
instead of joins so DISTINCT isn't needed and the count/page selects stay
identical in shape.

The keyword filter (``q``) is a case-insensitive substring scan via LIKE.
SQLite without FTS5 is plenty for v1 scale (a single user's journal
fits in a few thousand rows max). Revisit when search shows up slow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from fastapi import status
from sqlalchemy import (
    Select,
    exists,
    func,
    literal_column,
    or_,
    select,
)

from soap_journal.core.bible.books import get_book_by_name
from soap_journal.core.errors import ErrorCode, raise_http
from soap_journal.db.models.book import Book
from soap_journal.db.models.chapter import Chapter
from soap_journal.db.models.entry import Entry
from soap_journal.db.models.entry_scripture_verse import EntryScriptureVerse
from soap_journal.db.models.entry_tag import EntryTag
from soap_journal.db.models.tag import Tag
from soap_journal.db.models.verse import Verse


@dataclass(slots=True)
class EntryFilters:
    """Resolved, ready-to-apply filter inputs.

    ``book_canonical_name`` is the canonical form (e.g. "John") even if
    the user typed an alias. ``tag_lower`` is normalized for the
    case-insensitive lookup.
    """

    q: str | None = None
    book_canonical_name: str | None = None
    tag_lower: str | None = None
    from_date: date | None = None
    to_date: date | None = None


@dataclass(slots=True)
class AppliedFilterValues:
    """Echoed back in the response so the frontend can render filter chips."""

    q: str | None
    book: str | None
    tag: str | None
    from_date: date | None
    to_date: date | None


def resolve_filters(
    raw_q: str | None,
    raw_book: str | None,
    raw_tag: str | None,
    raw_from: date | None,
    raw_to: date | None,
) -> tuple[EntryFilters, AppliedFilterValues]:
    """Validate raw query params, normalize, return both the filter and
    the echo. May raise 400 for bad book / invalid date range."""
    q_stripped = (raw_q or "").strip()
    q_value = q_stripped if q_stripped else None

    canonical_book: str | None = None
    if raw_book is not None and raw_book.strip():
        canon = get_book_by_name(raw_book.strip())
        if canon is None:
            raise_http(
                status.HTTP_400_BAD_REQUEST,
                ErrorCode.INVALID_BOOK,
                f"unknown book: {raw_book!r}",
            )
        canonical_book = canon.name

    tag_value: str | None = None
    tag_lower: str | None = None
    if raw_tag is not None and raw_tag.strip():
        tag_value = raw_tag.strip()
        tag_lower = tag_value.lower()

    if raw_from is not None and raw_to is not None and raw_from > raw_to:
        raise_http(
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.INVALID_DATE_RANGE,
            f"from_date {raw_from.isoformat()} is after to_date {raw_to.isoformat()}",
        )

    filters = EntryFilters(
        q=q_value,
        book_canonical_name=canonical_book,
        tag_lower=tag_lower,
        from_date=raw_from,
        to_date=raw_to,
    )
    applied = AppliedFilterValues(
        q=q_value,
        book=canonical_book,
        tag=tag_value,
        from_date=raw_from,
        to_date=raw_to,
    )
    return filters, applied


def _escape_like(value: str) -> str:
    """Escape SQL LIKE wildcards so user input is a literal substring."""
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def apply_filters(stmt: Select, user_id: int, filters: EntryFilters) -> Select:
    """Add user-scoping and filter predicates to a count or page select."""
    stmt = stmt.where(Entry.user_id == user_id)

    if filters.q:
        like_pattern = f"%{_escape_like(filters.q.lower())}%"
        # title is nullable; func.lower(NULL) → NULL → false in WHERE OR, so
        # null titles are naturally excluded from the title match (and the
        # row still passes if it matches any of the other fields).
        stmt = stmt.where(
            or_(
                func.lower(Entry.title).like(like_pattern, escape="\\"),
                func.lower(Entry.observation).like(like_pattern, escape="\\"),
                func.lower(Entry.application).like(like_pattern, escape="\\"),
                func.lower(Entry.prayer).like(like_pattern, escape="\\"),
                func.lower(Entry.scripture_text).like(like_pattern, escape="\\"),
            )
        )

    if filters.book_canonical_name is not None:
        # EXISTS keeps the outer row set unique without DISTINCT.
        book_clause = exists(
            select(literal_column("1"))
            .select_from(EntryScriptureVerse)
            .join(Verse, Verse.id == EntryScriptureVerse.verse_id)
            .join(Chapter, Chapter.id == Verse.chapter_id)
            .join(Book, Book.id == Chapter.book_id)
            .where(
                EntryScriptureVerse.entry_id == Entry.id,
                Book.name == filters.book_canonical_name,
            )
        )
        stmt = stmt.where(book_clause)

    if filters.tag_lower is not None:
        tag_clause = exists(
            select(literal_column("1"))
            .select_from(EntryTag)
            .join(Tag, Tag.id == EntryTag.tag_id)
            .where(
                EntryTag.entry_id == Entry.id,
                Tag.user_id == user_id,
                Tag.name_lower == filters.tag_lower,
            )
        )
        stmt = stmt.where(tag_clause)

    if filters.from_date is not None:
        stmt = stmt.where(Entry.entry_date >= filters.from_date)
    if filters.to_date is not None:
        stmt = stmt.where(Entry.entry_date <= filters.to_date)

    return stmt


__all__ = [
    "AppliedFilterValues",
    "EntryFilters",
    "apply_filters",
    "resolve_filters",
]
