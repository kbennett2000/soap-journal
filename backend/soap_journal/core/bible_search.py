"""Full-text search over verse text and translator's notes (SQLite FTS5).

Distinct from the entry keyword search (`core/entries_query.py`): that scans a
single user's private journal with LIKE; this is bm25-ranked FTS5 over the
shared scripture + notes corpus. The two are deliberately separate features over
separate data. See docs/adr/0003-full-text-search.md.

This module is the single-translation path (ADR-0003 Cycle 2): both FTS tables
are filtered by the resolved `translation_id`. The cross-translation `ALL` mode
(grouping per canonical verse) is a later cycle.

Query sanitisation mirrors the NET app: input containing a `"` is treated as a
power-user phrase expression and passed through verbatim; otherwise it is
tokenised on whitespace, FTS5 reserved characters are stripped, and the tokens
are quoted and ANDed. A passed-through expression that turns out to be malformed
raises a driver `OperationalError`, which is caught and degraded to empty
results so an odd query never 500s.
"""

from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.schemas.bible import (
    NoteSearchHit,
    SearchResponse,
    SearchScope,
    VerseSearchHit,
)

# FTS5 reserved characters stripped from bare (unquoted) tokens so a casual
# query never trips FTS5 syntax.
_RESERVED_FTS5_CHARS = re.compile(r'[()":*\-]')


def _sanitize(raw: str) -> str | None:
    """Return an FTS5 MATCH expression, or None if empty after cleanup.

    Quoted input passes through (power-user phrase syntax); bare input is
    tokenised, stripped of reserved chars, quoted per-token, and ANDed.
    """
    s = raw.strip()
    if not s:
        return None
    if '"' in s:
        return s
    tokens = [_RESERVED_FTS5_CHARS.sub("", t) for t in s.split()]
    tokens = [t for t in tokens if t]
    if not tokens:
        return None
    return " ".join(f'"{t}"' for t in tokens)


_VERSE_SEARCH_SQL = text(
    "SELECT b.abbreviation AS book, c.number AS chapter, v.number AS verse, "
    "snippet(verses_fts, 0, '<mark>', '</mark>', '…', 32) AS snippet "
    "FROM verses_fts "
    "JOIN verses v ON v.id = verses_fts.rowid "
    "JOIN chapters c ON c.id = v.chapter_id "
    "JOIN books b ON b.id = c.book_id "
    "WHERE verses_fts MATCH :q AND verses_fts.translation_id = :tid "
    "ORDER BY rank "
    "LIMIT :limit OFFSET :offset"
)
_VERSE_COUNT_SQL = text(
    "SELECT count(*) FROM verses_fts WHERE verses_fts MATCH :q AND verses_fts.translation_id = :tid"
)
_NOTE_SEARCH_SQL = text(
    "SELECT b.abbreviation AS book, c.number AS chapter, v.number AS verse, "
    "notes_fts.note_type AS note_type, "
    "snippet(notes_fts, 0, '<mark>', '</mark>', '…', 48) AS snippet "
    "FROM notes_fts "
    "JOIN footnotes f ON f.id = notes_fts.rowid "
    "JOIN verses v ON v.id = f.verse_id "
    "JOIN chapters c ON c.id = v.chapter_id "
    "JOIN books b ON b.id = c.book_id "
    "WHERE notes_fts MATCH :q AND notes_fts.translation_id = :tid "
    "ORDER BY rank "
    "LIMIT :limit OFFSET :offset"
)
_NOTE_COUNT_SQL = text(
    "SELECT count(*) FROM notes_fts WHERE notes_fts MATCH :q AND notes_fts.translation_id = :tid"
)


async def run_search(
    db: AsyncSession,
    *,
    q: str,
    translation_code: str,
    translation_id: int,
    scope: SearchScope,
    limit: int,
    offset: int,
) -> SearchResponse:
    """Search one translation's verses and/or notes. Always returns 200-shaped
    data — a query that sanitises to nothing, or a malformed phrase expression,
    yields empty result lists rather than an error."""
    match_expr = _sanitize(q)

    verse_hits: list[VerseSearchHit] = []
    note_hits: list[NoteSearchHit] = []
    total_verse_hits = 0
    total_note_hits = 0

    if match_expr is not None:
        params = {"q": match_expr, "tid": translation_id, "limit": limit, "offset": offset}
        count_params = {"q": match_expr, "tid": translation_id}
        try:
            if scope in ("verses", "both"):
                rows = (await db.execute(_VERSE_SEARCH_SQL, params)).mappings().all()
                verse_hits = [
                    VerseSearchHit(
                        translation_code=translation_code,
                        book=r["book"],
                        chapter=r["chapter"],
                        verse=r["verse"],
                        snippet=r["snippet"],
                    )
                    for r in rows
                ]
                total_verse_hits = (await db.execute(_VERSE_COUNT_SQL, count_params)).scalar_one()
            if scope in ("notes", "both"):
                rows = (await db.execute(_NOTE_SEARCH_SQL, params)).mappings().all()
                note_hits = [
                    NoteSearchHit(
                        translation_code=translation_code,
                        book=r["book"],
                        chapter=r["chapter"],
                        verse=r["verse"],
                        note_type=r["note_type"],
                        snippet=r["snippet"],
                    )
                    for r in rows
                ]
                total_note_hits = (await db.execute(_NOTE_COUNT_SQL, count_params)).scalar_one()
        except OperationalError:
            # Malformed FTS5 phrase expression (e.g. an unbalanced quote passed
            # through). Degrade to empty results rather than 500. No further
            # queries run after the error, so the session stays usable.
            verse_hits = []
            note_hits = []
            total_verse_hits = 0
            total_note_hits = 0

    return SearchResponse(
        query=q,
        scope=scope,
        translation_code=translation_code,
        verse_hits=verse_hits,
        note_hits=note_hits,
        total_verse_hits=total_verse_hits,
        total_note_hits=total_note_hits,
        limit=limit,
        offset=offset,
    )
