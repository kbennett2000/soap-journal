"""Tests for the headless backup import/merge engine.

These are the design-teeth for cycle 2a: dedup keyed on created_at, last-write-
wins by updated_at, idempotency, lenient verse links, missing-translation skip,
the onupdate write trap, and the SQLite naive-datetime compare trap. Inputs are
built as ``BackupDocument`` objects; existing rows are seeded directly so the
timestamps under test are exact. ``bsb_loaded`` supplies real verses so the
reverse coordinate join resolves.
"""

from __future__ import annotations

import time
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.core.backup_import import import_backup
from soap_journal.core.entries import resolve_tags
from soap_journal.db.models.entry import Entry
from soap_journal.db.models.entry_scripture_verse import EntryScriptureVerse
from soap_journal.db.models.tag import Tag
from soap_journal.db.models.translation import Translation
from soap_journal.db.models.user import User
from soap_journal.schemas.backup import BackupDocument, BackupEntry, BackupVerse

# ---- builders --------------------------------------------------------------


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _verse(book_order_index: int, chapter: int, verse: int) -> BackupVerse:
    return BackupVerse(book_order_index=book_order_index, chapter=chapter, verse=verse)


# A real Romans 8:28 coordinate (Romans = book 45 in the BSB).
ROM_8_28 = _verse(45, 8, 28)
JOHN_3_16 = _verse(43, 3, 16)


def _file_entry(
    *,
    created_at: datetime,
    updated_at: datetime,
    title: str | None = None,
    entry_date: str = "2026-01-15",
    scripture_ref: str = "John 3:16",
    scripture_translation_code: str = "BSB",
    scripture_text: str = "For God so loved the world.",
    observation: str = "obs",
    application: str = "app",
    prayer: str = "pray",
    verses: list[BackupVerse] | None = None,
    tags: list[str] | None = None,
) -> BackupEntry:
    return BackupEntry(
        title=title,
        entry_date=entry_date,
        scripture_ref=scripture_ref,
        scripture_translation_code=scripture_translation_code,
        scripture_text=scripture_text,
        observation=observation,
        application=application,
        prayer=prayer,
        created_at=_iso(created_at),
        updated_at=_iso(updated_at),
        verses=[JOHN_3_16] if verses is None else verses,
        tags=tags if tags is not None else [],
    )


def _doc(*entries: BackupEntry) -> BackupDocument:
    return BackupDocument(exported_at="2026-06-03T17:00:00Z", entries=list(entries))


# ---- db helpers ------------------------------------------------------------


async def _make_user(db: AsyncSession, username: str = "alice") -> int:
    user = User(username=username, password_hash="x")
    db.add(user)
    await db.flush()
    return user.id


async def _bsb_id(db: AsyncSession) -> int:
    return (
        await db.execute(select(Translation.id).where(Translation.code == "BSB"))
    ).scalar_one()


async def _seed_entry(
    db: AsyncSession,
    user_id: int,
    translation_id: int,
    *,
    created_at: datetime,
    updated_at: datetime,
    scripture_ref: str = "John 3:16",
    title: str | None = None,
    scripture_text: str = "orig text",
    observation: str = "",
    application: str = "",
    prayer: str = "",
    verse_ids: tuple[int, ...] = (),
) -> Entry:
    entry = Entry(
        user_id=user_id,
        title=title,
        entry_date=date(2026, 1, 1),
        scripture_ref=scripture_ref,
        scripture_translation_id=translation_id,
        scripture_text=scripture_text,
        observation=observation,
        application=application,
        prayer=prayer,
        created_at=created_at,
        updated_at=updated_at,
    )
    db.add(entry)
    await db.flush()
    for verse_id in verse_ids:
        db.add(EntryScriptureVerse(entry_id=entry.id, verse_id=verse_id))
    await db.flush()
    return entry


async def _commit_and_expire(db: AsyncSession) -> None:
    """Commit (as the real caller would) and drop ORM state so subsequent reads
    come back from SQLite as NAIVE datetimes — exercising the compare trap."""
    await db.commit()
    db.expire_all()


async def _entries(db: AsyncSession, user_id: int) -> list[Entry]:
    return list(
        (
            await db.execute(
                select(Entry).where(Entry.user_id == user_id).order_by(Entry.id)
            )
        )
        .scalars()
        .all()
    )


async def _verse_ids(db: AsyncSession, entry_id: int) -> list[int]:
    return list(
        (
            await db.execute(
                select(EntryScriptureVerse.verse_id)
                .where(EntryScriptureVerse.entry_id == entry_id)
                .order_by(EntryScriptureVerse.verse_id)
            )
        )
        .scalars()
        .all()
    )


# ---- INSERT ----------------------------------------------------------------


async def test_insert_into_empty_journal(
    bsb_loaded: None, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    created = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    updated = datetime(2026, 1, 16, 9, 30, 0, tzinfo=UTC)
    doc = _doc(
        _file_entry(
            created_at=created,
            updated_at=updated,
            title="Imported",
            entry_date="2026-01-15",
            scripture_ref="Romans 8:28",
            scripture_text="And we know that God works all things...",
            verses=[ROM_8_28],
            tags=["faith", "Grace"],
        )
    )

    report = await import_backup(db_session, user_id, doc)

    assert (report.inserted, report.updated, report.skipped_unchanged) == (1, 0, 0)
    assert report.total_in_file == 1
    (entry,) = await _entries(db_session, user_id)
    assert entry.title == "Imported"
    assert entry.entry_date == date(2026, 1, 15)
    assert entry.scripture_ref == "Romans 8:28"  # verbatim, not re-parsed
    assert entry.scripture_text.startswith("And we know")  # verbatim, not re-snapshotted
    assert _norm(entry.created_at) == created
    assert _norm(entry.updated_at) == updated
    assert len(await _verse_ids(db_session, entry.id)) == 1  # Romans 8:28 resolved
    assert {t.name for t in await _tags_for(db_session, entry.id)} == {"faith", "Grace"}


# ---- IDEMPOTENCY -----------------------------------------------------------


async def test_idempotent_reimport_changes_nothing(
    bsb_loaded: None, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    doc = _doc(
        _file_entry(
            created_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2026, 1, 16, 9, 30, 0, tzinfo=UTC),
            verses=[JOHN_3_16],
            tags=["faith"],
        )
    )

    first = await import_backup(db_session, user_id, doc)
    assert first.inserted == 1
    await _commit_and_expire(db_session)
    before = await _entries(db_session, user_id)
    before_ts = (_norm(before[0].created_at), _norm(before[0].updated_at))

    second = await import_backup(db_session, user_id, doc)
    assert (second.inserted, second.updated, second.skipped_unchanged) == (0, 0, 1)
    after = await _entries(db_session, user_id)
    assert len(after) == 1
    assert (_norm(after[0].created_at), _norm(after[0].updated_at)) == before_ts


# ---- LWW UPDATE (onupdate guard) -------------------------------------------


async def test_lww_update_preserves_file_updated_at_not_now(
    bsb_loaded: None, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    translation_id = await _bsb_id(db_session)
    created = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    old_updated = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    await _seed_entry(
        db_session,
        user_id,
        translation_id,
        created_at=created,
        updated_at=old_updated,
        scripture_ref="John 3:16",
        title="Old",
        scripture_text="old text",
    )
    await _commit_and_expire(db_session)

    file_updated = datetime(2026, 2, 1, 8, 0, 0, tzinfo=UTC)  # newer, but NOT now()
    doc = _doc(
        _file_entry(
            created_at=created,
            updated_at=file_updated,
            title="New",
            scripture_ref="John 3:17",  # ref changed too
            scripture_text="new text",
            verses=[JOHN_3_16],
            tags=["hope"],
        )
    )

    report = await import_backup(db_session, user_id, doc)
    assert (report.inserted, report.updated) == (0, 1)
    await _commit_and_expire(db_session)

    (entry,) = await _entries(db_session, user_id)
    assert entry.title == "New"
    assert entry.scripture_text == "new text"
    assert entry.scripture_ref == "John 3:17"
    # The onupdate=_utcnow trap: updated_at must equal the FILE's value.
    assert _norm(entry.updated_at) == file_updated


# ---- LWW SKIP --------------------------------------------------------------


async def test_lww_skip_when_not_newer(
    bsb_loaded: None, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    translation_id = await _bsb_id(db_session)
    created = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    existing_updated = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)
    await _seed_entry(
        db_session,
        user_id,
        translation_id,
        created_at=created,
        updated_at=existing_updated,
        title="Keep me",
        scripture_text="keep",
    )
    await _commit_and_expire(db_session)

    # Same created_at, OLDER updated_at -> skip.
    doc = _doc(
        _file_entry(
            created_at=created,
            updated_at=datetime(2026, 2, 1, 0, 0, 0, tzinfo=UTC),
            title="Should not win",
            scripture_text="loser",
        )
    )
    report = await import_backup(db_session, user_id, doc)
    assert (report.updated, report.skipped_unchanged) == (0, 1)
    await _commit_and_expire(db_session)

    (entry,) = await _entries(db_session, user_id)
    assert entry.title == "Keep me"
    assert entry.scripture_text == "keep"
    assert _norm(entry.updated_at) == existing_updated  # not bumped


# ---- REF EDIT --------------------------------------------------------------


async def test_ref_edit_updates_not_duplicates(
    bsb_loaded: None, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    translation_id = await _bsb_id(db_session)
    created = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    await _seed_entry(
        db_session,
        user_id,
        translation_id,
        created_at=created,
        updated_at=created,
        scripture_ref="John 3:16",
    )
    await _commit_and_expire(db_session)

    doc = _doc(
        _file_entry(
            created_at=created,
            updated_at=datetime(2026, 2, 1, 0, 0, 0, tzinfo=UTC),
            scripture_ref="Romans 8:28",  # different ref, same created_at
            verses=[ROM_8_28],
        )
    )
    report = await import_backup(db_session, user_id, doc)
    assert (report.inserted, report.updated) == (0, 1)
    await _commit_and_expire(db_session)

    entries = await _entries(db_session, user_id)
    assert len(entries) == 1  # matched by created_at, not duplicated
    assert entries[0].scripture_ref == "Romans 8:28"


# ---- COLLISION tiebreaker --------------------------------------------------


async def test_collision_tiebreaker_matches_by_ref(
    bsb_loaded: None, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    translation_id = await _bsb_id(db_session)
    created = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    # Two existing entries share an EXACT created_at.
    await _seed_entry(
        db_session, user_id, translation_id,
        created_at=created, updated_at=created,
        scripture_ref="John 3:16", title="A",
    )
    await _seed_entry(
        db_session, user_id, translation_id,
        created_at=created, updated_at=created,
        scripture_ref="Romans 8:28", title="B",
    )
    await _commit_and_expire(db_session)

    # Matching ref -> updates the right one.
    doc = _doc(
        _file_entry(
            created_at=created,
            updated_at=datetime(2026, 2, 1, 0, 0, 0, tzinfo=UTC),
            scripture_ref="Romans 8:28",
            title="B-updated",
            verses=[ROM_8_28],
        )
    )
    report = await import_backup(db_session, user_id, doc)
    assert (report.inserted, report.updated) == (0, 1)
    await _commit_and_expire(db_session)

    by_ref = {e.scripture_ref: e for e in await _entries(db_session, user_id)}
    assert by_ref["John 3:16"].title == "A"  # untouched
    assert by_ref["Romans 8:28"].title == "B-updated"
    assert len(await _entries(db_session, user_id)) == 2


async def test_collision_non_matching_ref_inserts(
    bsb_loaded: None, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    translation_id = await _bsb_id(db_session)
    created = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    await _seed_entry(
        db_session, user_id, translation_id,
        created_at=created, updated_at=created, scripture_ref="John 3:16", title="A",
    )
    await _seed_entry(
        db_session, user_id, translation_id,
        created_at=created, updated_at=created, scripture_ref="Romans 8:28", title="B",
    )
    await _commit_and_expire(db_session)

    # Ambiguous bucket (>1) + a ref that matches NEITHER -> insert, never guess.
    doc = _doc(
        _file_entry(
            created_at=created,
            updated_at=datetime(2026, 2, 1, 0, 0, 0, tzinfo=UTC),
            scripture_ref="Psalm 23:1",
            title="C",
            verses=[_verse(19, 23, 1)],
        )
    )
    report = await import_backup(db_session, user_id, doc)
    assert (report.inserted, report.updated) == (1, 0)
    await _commit_and_expire(db_session)
    assert len(await _entries(db_session, user_id)) == 3


# ---- MISSING TRANSLATION ---------------------------------------------------


async def test_missing_translation_skips_entry_not_run(
    bsb_loaded: None, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    base = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    doc = _doc(
        _file_entry(
            created_at=base,
            updated_at=base,
            scripture_translation_code="ESV",  # not loaded
            scripture_ref="John 3:16",
        ),
        _file_entry(
            created_at=base + timedelta(minutes=1),
            updated_at=base + timedelta(minutes=1),
            scripture_translation_code="BSB",  # loaded -> imports
            scripture_ref="Romans 8:28",
            verses=[ROM_8_28],
        ),
    )

    report = await import_backup(db_session, user_id, doc)
    assert report.inserted == 1
    assert report.skipped_missing_translation == 1
    assert report.missing_translations == ["ESV"]
    assert report.total_in_file == 2
    (entry,) = await _entries(db_session, user_id)
    assert entry.scripture_ref == "Romans 8:28"


# ---- LENIENT VERSES --------------------------------------------------------


async def test_unresolvable_verse_is_skipped_entry_still_imports(
    bsb_loaded: None, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    created = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    doc = _doc(
        _file_entry(
            created_at=created,
            updated_at=created,
            scripture_ref="Romans 8:28",
            scripture_text="self-contained text",
            verses=[ROM_8_28, _verse(45, 8, 999)],  # second is out of range
        )
    )
    report = await import_backup(db_session, user_id, doc)
    assert report.inserted == 1
    (entry,) = await _entries(db_session, user_id)
    assert entry.scripture_text == "self-contained text"
    assert len(await _verse_ids(db_session, entry.id)) == 1  # only the valid link


# ---- TIMESTAMP under a non-UTC zone ----------------------------------------


async def test_timestamp_preserved_under_non_utc_zone(
    bsb_loaded: None, db_session: AsyncSession, monkeypatch
) -> None:
    monkeypatch.setenv("TZ", "America/Denver")
    time.tzset()
    try:
        user_id = await _make_user(db_session)
        created = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
        updated = datetime(2026, 1, 16, 18, 0, 0, tzinfo=UTC)
        doc = _doc(_file_entry(created_at=created, updated_at=updated))

        report = await import_backup(db_session, user_id, doc)
        assert report.inserted == 1
        await _commit_and_expire(db_session)  # force naive reload from SQLite

        (entry,) = await _entries(db_session, user_id)
        # Naive DB value must be read as UTC, not shifted by Denver.
        assert _norm(entry.created_at) == created
        assert _norm(entry.updated_at) == updated

        # And a re-import must still dedup to SKIP (compare can't be tz-confused).
        again = await import_backup(db_session, user_id, doc)
        assert (again.updated, again.skipped_unchanged) == (0, 1)
    finally:
        monkeypatch.undo()
        time.tzset()


# ---- ATOMICITY / no partial write ------------------------------------------


# The explicit rollback below deassociates conftest's externally-begun
# transaction, so its teardown rollback warns. That's a fixture artifact, not an
# engine issue — the rollback is exactly what proves the pending write vanishes.
@pytest.mark.filterwarnings("ignore:transaction already deassociated")
async def test_engine_does_not_commit_and_leaves_no_partial_write(
    bsb_loaded: None, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    good = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    doc = _doc(
        _file_entry(created_at=good, updated_at=good, scripture_ref="John 3:16"),
        # Malformed timestamp -> _parse_instant raises mid-run, AFTER the first
        # entry has been added+flushed (but never committed).
        BackupEntry(
            title=None,
            entry_date="2026-01-15",
            scripture_ref="Romans 8:28",
            scripture_translation_code="BSB",
            scripture_text="x",
            observation="",
            application="",
            prayer="",
            created_at="not-a-timestamp",
            updated_at="not-a-timestamp",
            verses=[],
            tags=[],
        ),
    )

    with pytest.raises(ValueError):
        await import_backup(db_session, user_id, doc)

    # The engine never committed; the caller rolls back -> nothing persisted.
    await db_session.rollback()
    assert await _entry_count(db_session, user_id) == 0


# ---- MULTI-USER ------------------------------------------------------------


async def test_dedup_is_scoped_to_user(
    bsb_loaded: None, db_session: AsyncSession
) -> None:
    translation_id = await _bsb_id(db_session)
    alice = await _make_user(db_session, "alice")
    bob = await _make_user(db_session, "bob")
    shared_created = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    # Alice already has an entry at this exact created_at.
    await _seed_entry(
        db_session, alice, translation_id,
        created_at=shared_created, updated_at=shared_created,
        scripture_ref="John 3:16", title="alice-orig",
    )
    await _commit_and_expire(db_session)

    # Bob imports an entry with the SAME created_at -> must INSERT under Bob,
    # never match Alice's row.
    doc = _doc(
        _file_entry(
            created_at=shared_created,
            updated_at=datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC),
            title="bob-import",
        )
    )
    report = await import_backup(db_session, bob, doc)
    assert report.inserted == 1
    await _commit_and_expire(db_session)

    alice_entries = await _entries(db_session, alice)
    bob_entries = await _entries(db_session, bob)
    assert [e.title for e in alice_entries] == ["alice-orig"]  # untouched
    assert [e.title for e in bob_entries] == ["bob-import"]


# ---- TAG get-or-create -----------------------------------------------------


async def test_tags_reuse_existing_and_create_missing(
    bsb_loaded: None, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    # Pre-existing tag with specific casing.
    await resolve_tags(db_session, user_id, ["Faith"])
    await _commit_and_expire(db_session)

    created = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    doc = _doc(
        _file_entry(created_at=created, updated_at=created, tags=["faith", "Hope"])
    )
    report = await import_backup(db_session, user_id, doc)
    assert report.inserted == 1
    await _commit_and_expire(db_session)

    tag_count = (
        await db_session.execute(
            select(func.count()).select_from(Tag).where(Tag.user_id == user_id)
        )
    ).scalar_one()
    assert tag_count == 2  # Faith reused, Hope created — no duplicate
    (entry,) = await _entries(db_session, user_id)
    names = {t.name for t in await _tags_for(db_session, entry.id)}
    assert names == {"Faith", "Hope"}  # original casing of the reused tag wins


# ---- DRY RUN ---------------------------------------------------------------


async def test_dry_run_reports_but_writes_nothing(
    bsb_loaded: None, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    await _commit_and_expire(db_session)
    created = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    doc = _doc(
        _file_entry(created_at=created, updated_at=created, tags=["brandnew"], verses=[ROM_8_28],
                    scripture_ref="Romans 8:28")
    )

    report = await import_backup(db_session, user_id, doc, dry_run=True)
    assert report.dry_run is True
    assert (report.inserted, report.updated, report.skipped_unchanged) == (1, 0, 0)

    assert await _entry_count(db_session, user_id) == 0
    tag_count = (
        await db_session.execute(
            select(func.count()).select_from(Tag).where(Tag.user_id == user_id)
        )
    ).scalar_one()
    assert tag_count == 0


# ---- small read helpers used above -----------------------------------------


def _norm(dt: datetime) -> datetime:
    return (dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt).astimezone(UTC)


async def _tags_for(db: AsyncSession, entry_id: int) -> list[Tag]:
    from soap_journal.db.models.entry_tag import EntryTag

    return list(
        (
            await db.execute(
                select(Tag).join(EntryTag, EntryTag.tag_id == Tag.id).where(
                    EntryTag.entry_id == entry_id
                )
            )
        )
        .scalars()
        .all()
    )


async def _entry_count(db: AsyncSession, user_id: int) -> int:
    return (
        await db.execute(
            select(func.count()).select_from(Entry).where(Entry.user_id == user_id)
        )
    ).scalar_one()
