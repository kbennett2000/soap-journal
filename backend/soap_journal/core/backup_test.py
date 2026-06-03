"""Tests for the headless backup builder.

Entries are seeded via the API client (so the real save-time scripture
pipeline runs and links verses), then ``build_backup`` is invoked directly
against the same ``db_session``. The ``_iso_z`` timezone guard is exercised by a
dedicated unit test under a pinned non-UTC zone — see its docstring for why that
zone is REQUIRED, not optional.
"""

from __future__ import annotations

import time
from datetime import UTC, date, datetime

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.core.backup import _iso_z, build_backup
from soap_journal.db.models.entry import Entry
from soap_journal.db.models.translation import Translation
from soap_journal.db.models.user import User

# ---- helpers ---------------------------------------------------------------


async def _register(client: AsyncClient, username: str = "alice") -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "password123"},
    )
    assert response.status_code == 201, response.text


async def _create_entry(client: AsyncClient, **fields) -> dict:
    payload = {"scripture_ref": "John 3:16"} | fields
    response = await client.post("/api/v1/entries", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["entry"]


async def _user_id(db: AsyncSession, username: str = "alice") -> int:
    return (
        await db.execute(select(User.id).where(User.username == username))
    ).scalar_one()


# ---- _iso_z timezone guard (load-bearing) ----------------------------------


def test_iso_z_treats_naive_as_utc_not_local(monkeypatch) -> None:
    """The SQLite dialect hands back NAIVE datetimes whose wall-clock is UTC.

    The buggy ``naive.astimezone(UTC)`` is a literal no-op under TZ=UTC (CI's
    default), so this assertion only catches the bug when run under a non-UTC
    zone — hence pinning America/Denver is required, not optional.
    """
    monkeypatch.setenv("TZ", "America/Denver")
    time.tzset()
    try:
        # A naive wall-clock must NOT be shifted by the server's local zone.
        assert _iso_z(datetime(2026, 1, 1, 12, 0, 0)) == "2026-01-01T12:00:00Z"
    finally:
        monkeypatch.undo()
        time.tzset()  # REQUIRED: monkeypatch restores the env var but won't
        # re-run tzset(); without this the process keeps Denver time and leaks
        # confusing failures into later tests.


def test_iso_z_normalizes_aware_offset_to_z() -> None:
    from datetime import timedelta, timezone

    aware = datetime(2026, 1, 1, 7, 0, 0, tzinfo=timezone(timedelta(hours=-5)))
    assert _iso_z(aware) == "2026-01-01T12:00:00Z"


# ---- build_backup ----------------------------------------------------------


async def test_empty_journal_yields_valid_empty_document(
    client: AsyncClient, bsb_loaded: None, db_session: AsyncSession
) -> None:
    await _register(client)
    exported_at = datetime(2026, 6, 3, 17, 0, 0, tzinfo=UTC)

    document = await build_backup(db_session, await _user_id(db_session), exported_at)

    assert document.format == "soap-journal-backup"
    assert document.version == 1
    assert document.exported_at == "2026-06-03T17:00:00Z"
    assert document.entries == []


async def test_entry_with_tags_and_multiverse_ref(
    client: AsyncClient, bsb_loaded: None, db_session: AsyncSession
) -> None:
    await _register(client)
    await _create_entry(
        client,
        scripture_ref="Romans 8:28-30",
        tags=["Grace", "faith", "Hope"],
    )

    document = await build_backup(
        db_session, await _user_id(db_session), datetime.now(UTC)
    )

    assert len(document.entries) == 1
    entry = document.entries[0]
    assert entry.scripture_ref == "Romans 8:28-30"
    assert entry.scripture_translation_code == "BSB"

    # Romans is book 45; chapter 8; verses 28, 29, 30 — ordered.
    assert [(v.book_order_index, v.chapter, v.verse) for v in entry.verses] == [
        (45, 8, 28),
        (45, 8, 29),
        (45, 8, 30),
    ]

    # Tag NAMES, original casing, ordered by lower(name): faith, Grace, Hope.
    assert entry.tags == ["faith", "Grace", "Hope"]


async def test_entry_with_zero_linked_verses(
    client: AsyncClient, bsb_loaded: None, db_session: AsyncSession
) -> None:
    # Every API-created entry links at least one verse, so insert a bare entry
    # (no entry_scripture_verses) directly to exercise the verses: [] path.
    await _register(client)
    user_id = await _user_id(db_session)
    translation_id = (
        await db_session.execute(select(Translation.id).where(Translation.code == "BSB"))
    ).scalar_one()
    db_session.add(
        Entry(
            user_id=user_id,
            title=None,
            entry_date=date(2026, 1, 1),
            scripture_ref="Genesis 1:1",
            scripture_translation_id=translation_id,
            scripture_text="",
            observation="",
            application="",
            prayer="",
        )
    )
    await db_session.flush()

    document = await build_backup(db_session, user_id, datetime.now(UTC))

    assert len(document.entries) == 1
    assert document.entries[0].verses == []


async def test_timestamps_round_trip_to_stored_instant(
    client: AsyncClient, bsb_loaded: None, db_session: AsyncSession
) -> None:
    await _register(client)
    await _create_entry(client, scripture_ref="John 3:16")
    stored = (
        await db_session.execute(select(Entry.created_at, Entry.updated_at))
    ).one()

    document = await build_backup(
        db_session, await _user_id(db_session), datetime.now(UTC)
    )
    entry = document.entries[0]

    for emitted, raw in ((entry.created_at, stored[0]), (entry.updated_at, stored[1])):
        assert emitted.endswith("Z")
        # The exported instant must equal the DB value interpreted as UTC. If
        # the helper shifted by the host zone this comparison would fail.
        reparsed = datetime.fromisoformat(emitted.replace("Z", "+00:00"))
        expected = raw if raw.tzinfo is not None else raw.replace(tzinfo=UTC)
        assert reparsed == expected


async def test_entries_ordered_by_created_at_then_id(
    client: AsyncClient, bsb_loaded: None, db_session: AsyncSession
) -> None:
    await _register(client)
    # Created oldest-first, but with entry_date DESCENDING, so ordering by
    # created_at (not entry_date) is observable in the result.
    await _create_entry(client, scripture_ref="John 3:16", entry_date="2026-03-03")
    await _create_entry(client, scripture_ref="John 3:17", entry_date="2026-02-02")
    await _create_entry(client, scripture_ref="John 3:18", entry_date="2026-01-01")

    document = await build_backup(
        db_session, await _user_id(db_session), datetime.now(UTC)
    )

    assert [e.scripture_ref for e in document.entries] == [
        "John 3:16",
        "John 3:17",
        "John 3:18",
    ]
