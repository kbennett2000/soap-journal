"""Headless merge engine for journal backup import (FORMAT version 1).

``import_backup`` folds an already-parsed ``BackupDocument`` (the cycle-1 export
shape, the same files the mobile app produces) into one user's journal with
last-write-wins, idempotently. It is the reverse of ``core/backup.py``.

Design decisions (binding):

1. FIDELITY — the file is the source of truth for content. Title, dates,
   ``scripture_ref``, ``scripture_text`` and the SOAP fields are stored VERBATIM.
   The ref is never re-parsed and the text is never re-snapshotted from the
   desktop's Bible (that would rewrite the entry to the desktop edition or fail
   when the translation is absent). This is why the import does NOT route through
   ``save_entry``.
2. LENIENT VERSE LINKS — each file verse coordinate (book_order_index, chapter,
   verse) is resolved to a local ``verse_id`` within the entry's translation (the
   reverse of cycle-1's join). A coordinate that doesn't resolve is skipped; the
   entry still imports (its text is self-contained).
3. MISSING TRANSLATION — ``Entry.scripture_translation_id`` is NOT NULL, so an
   entry whose code isn't loaded here cannot be inserted: it is skipped and its
   code reported. The run never aborts over it.
4. DEDUP + LWW — keyed on ``created_at`` (the only immutable field), scoped to the
   user; ``scripture_ref`` is a tiebreaker only when several existing entries share
   an exact ``created_at``. On a match, last-write-wins by ``updated_at``.
5. TIMESTAMPS — the file's instants are preserved. SQLite hands back NAIVE
   datetimes (stored wall-clock is UTC), so the DB side is normalized before any
   compare; writes assign AWARE UTC so imported rows read identically to native
   ones.

The engine mutates the session and flushes but NEVER commits — the caller owns
the transaction (commits iff not a dry run). ``dry_run=True`` performs no writes
and still returns accurate counts.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.core.entries import resolve_tags
from soap_journal.db.models.book import Book
from soap_journal.db.models.chapter import Chapter
from soap_journal.db.models.entry import Entry
from soap_journal.db.models.entry_scripture_verse import EntryScriptureVerse
from soap_journal.db.models.entry_tag import EntryTag
from soap_journal.db.models.translation import Translation
from soap_journal.db.models.verse import Verse
from soap_journal.schemas.backup import BackupDocument, BackupEntry, ImportReport


@dataclass(slots=True)
class _Candidate:
    """A dedup candidate within a created_at bucket.

    ``entry`` is the live ORM row for real applies; it is ``None`` for synthetic
    candidates recorded during a dry run (so later same-created_at file rows still
    dedup correctly and the counts stay honest).
    """

    updated: datetime  # normalized aware UTC
    scripture_ref: str
    entry: Entry | None


def _normalize(dt: datetime) -> datetime:
    """Coerce a possibly-naive datetime to aware UTC.

    SQLite returns naive datetimes whose wall-clock is UTC; comparing those
    against the file's aware instants (or string-comparing) would be wrong. Same
    fix as ``core/sessions.py:_normalize``.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _parse_instant(value: str) -> datetime:
    """Parse an ISO-8601 UTC string (trailing ``Z``) to an aware UTC instant.

    The file contract guarantees ISO-8601 timestamps (the import endpoint
    validates the document before calling). A malformed value raises; since the
    engine never commits, the caller's transaction rolls back with no partial
    write.
    """
    return _normalize(datetime.fromisoformat(value.replace("Z", "+00:00")))


def validate_backup_dates(document: BackupDocument) -> list[str]:
    """Return human-readable errors for any unparseable date/timestamp.

    The backup schema types ``entry_date``/``created_at``/``updated_at`` as plain
    ``str`` (the export schema stays as lenient as the phone's Zod), so a
    structurally-valid file can still carry a value that would ``ValueError``
    mid-engine. The import endpoint calls this up front so ``import_backup`` only
    ever runs on fully-valid input. Pure — no DB.
    """
    errors: list[str] = []
    for index, entry in enumerate(document.entries):
        try:
            date.fromisoformat(entry.entry_date)
            _parse_instant(entry.created_at)
            _parse_instant(entry.updated_at)
        except ValueError:
            errors.append(f"entry {index} has an invalid date or timestamp")
    return errors


async def _resolve_verse_ids(
    db: AsyncSession, translation_id: int, coords: list[tuple[int, int, int]]
) -> list[int]:
    """Reverse cycle-1's join: (book_order_index, chapter, verse) -> verse_id.

    One query per entry. Unresolvable coordinates are skipped (lenient). Result
    preserves input order and is de-duplicated to guard the
    ``(entry_id, verse_id)`` primary key.
    """
    if not coords:
        return []

    book_orders = {c[0] for c in coords}
    chapter_numbers = {c[1] for c in coords}
    verse_numbers = {c[2] for c in coords}

    rows = (
        await db.execute(
            select(Book.order_index, Chapter.number, Verse.number, Verse.id)
            .join(Chapter, Chapter.book_id == Book.id)
            .join(Verse, Verse.chapter_id == Chapter.id)
            .where(
                Book.translation_id == translation_id,
                Book.order_index.in_(book_orders),
                Chapter.number.in_(chapter_numbers),
                Verse.number.in_(verse_numbers),
            )
        )
    ).all()
    by_coord = {(oi, cn, vn): vid for oi, cn, vn, vid in rows}

    resolved: list[int] = []
    seen: set[int] = set()
    for coord in coords:
        verse_id = by_coord.get(coord)
        if verse_id is not None and verse_id not in seen:
            seen.add(verse_id)
            resolved.append(verse_id)
    return resolved


def _choose_match(bucket: list[_Candidate], scripture_ref: str) -> _Candidate | None:
    """Pick the dedup match within a created_at bucket.

    0 candidates -> no match (INSERT). Exactly 1 -> that one, ignoring ref (so a
    ref edit updates in place). >1 -> the one whose ref also matches, else no
    match (never guess — a duplicate beats a destructive merge).

    Assumes distinct entries never share an exact created_at (it is the immutable
    dedup key). Within a single file, two entries that DO share a created_at
    collapse via last-write-wins: the bucket already holds the 1st when the 2nd is
    processed, so the 2nd matches and updates in place.
    """
    if not bucket:
        return None
    if len(bucket) == 1:
        return bucket[0]
    for candidate in bucket:
        if candidate.scripture_ref == scripture_ref:
            return candidate
    return None


async def _apply_entry(
    db: AsyncSession,
    user_id: int,
    translation_id: int,
    file_entry: BackupEntry,
    created: datetime,
    updated: datetime,
    existing: Entry | None,
) -> Entry:
    """Write one file entry verbatim (INSERT or in-place UPDATE) + rebuild links."""
    if existing is None:
        entry = Entry(user_id=user_id)
        db.add(entry)
        entry.created_at = created
    else:
        entry = existing  # created_at left untouched — same instant by construction

    entry.title = file_entry.title
    entry.entry_date = date.fromisoformat(file_entry.entry_date)
    entry.scripture_ref = file_entry.scripture_ref
    entry.scripture_translation_id = translation_id
    entry.scripture_text = file_entry.scripture_text
    entry.observation = file_entry.observation
    entry.application = file_entry.application
    entry.prayer = file_entry.prayer
    # Explicit assignment lands updated_at in the UPDATE SET clause, which
    # suppresses the column's onupdate=_utcnow — we need the file's value, not now().
    entry.updated_at = updated
    await db.flush()  # need entry.id for the link tables

    # Rebuild verse links (delete-all-then-insert, mirroring save_entry).
    await db.execute(
        delete(EntryScriptureVerse)
        .where(EntryScriptureVerse.entry_id == entry.id)
        .execution_options(synchronize_session="fetch")
    )
    coords = [(v.book_order_index, v.chapter, v.verse) for v in file_entry.verses]
    for verse_id in await _resolve_verse_ids(db, translation_id, coords):
        db.add(EntryScriptureVerse(entry_id=entry.id, verse_id=verse_id))

    # Rebuild tag links via the shared get-or-create.
    tags = await resolve_tags(db, user_id, file_entry.tags)
    await db.execute(
        delete(EntryTag)
        .where(EntryTag.entry_id == entry.id)
        .execution_options(synchronize_session="fetch")
    )
    for tag in tags:
        db.add(EntryTag(entry_id=entry.id, tag_id=tag.id))

    await db.flush()
    return entry


async def import_backup(
    db: AsyncSession,
    user_id: int,
    document: BackupDocument,
    *,
    dry_run: bool = False,
) -> ImportReport:
    """Merge ``document`` into ``user_id``'s journal (last-write-wins, idempotent).

    Does NOT commit — the caller commits iff ``not dry_run``. With ``dry_run`` no
    writes or ORM mutations happen, but the returned counts match what a real run
    would produce.
    """
    report = ImportReport(total_in_file=len(document.entries), dry_run=dry_run)

    code_to_id = dict(
        (await db.execute(select(Translation.code, Translation.id))).all()
    )

    existing_entries = (
        (await db.execute(select(Entry).where(Entry.user_id == user_id)))
        .scalars()
        .all()
    )
    buckets: dict[datetime, list[_Candidate]] = defaultdict(list)
    for entry in existing_entries:
        buckets[_normalize(entry.created_at)].append(
            _Candidate(
                updated=_normalize(entry.updated_at),
                scripture_ref=entry.scripture_ref,
                entry=entry,
            )
        )

    missing: set[str] = set()

    for file_entry in document.entries:
        translation_id = code_to_id.get(file_entry.scripture_translation_code)
        if translation_id is None:
            report.skipped_missing_translation += 1
            missing.add(file_entry.scripture_translation_code)
            continue

        created = _parse_instant(file_entry.created_at)
        updated = _parse_instant(file_entry.updated_at)
        match = _choose_match(buckets[created], file_entry.scripture_ref)

        if match is not None and updated <= match.updated:
            report.skipped_unchanged += 1
            continue

        is_insert = match is None
        if is_insert:
            report.inserted += 1
        else:
            report.updated += 1

        if dry_run:
            # Reflect the decision in the dedup state so later same-created_at
            # file rows behave identically to a real run, without touching the DB.
            if is_insert:
                buckets[created].append(
                    _Candidate(updated=updated, scripture_ref=file_entry.scripture_ref, entry=None)
                )
            else:
                assert match is not None
                match.updated = updated
                match.scripture_ref = file_entry.scripture_ref
            continue

        entry = await _apply_entry(
            db,
            user_id,
            translation_id,
            file_entry,
            created,
            updated,
            None if is_insert else (match.entry if match else None),
        )

        if is_insert:
            buckets[created].append(
                _Candidate(updated=updated, scripture_ref=entry.scripture_ref, entry=entry)
            )
        else:
            assert match is not None
            match.updated = updated
            match.scripture_ref = entry.scripture_ref

    report.missing_translations = sorted(missing)
    return report
