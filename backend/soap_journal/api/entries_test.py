"""Tests for the SOAP journal entry endpoints.

All tests depend on the session-scoped `bsb_loaded` fixture so the
save-time scripture pipeline has real BSB data to resolve references
against.
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.db.models.entry import Entry
from soap_journal.db.models.entry_scripture_verse import EntryScriptureVerse
from soap_journal.db.models.entry_tag import EntryTag
from soap_journal.db.models.tag import Tag

# ---- helpers ---------------------------------------------------------------


async def _register(client: AsyncClient, username: str = "alice") -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "password123"},
    )
    assert response.status_code == 201, response.text


async def _create_entry(
    client: AsyncClient,
    **fields,
) -> dict:
    payload = {"scripture_ref": "John 3:16"} | fields
    response = await client.post("/api/v1/entries", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["entry"]


# ---- auth gating + cross-user isolation ------------------------------------


async def test_entries_list_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/entries")
    assert response.status_code == 401


async def test_entry_create_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.post("/api/v1/entries", json={"scripture_ref": "John 3:16"})
    assert response.status_code == 401


async def test_cannot_see_other_users_entry(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client, "alice")
    entry = await _create_entry(client, scripture_ref="John 3:16")
    alice_entry_id = entry["id"]

    # Admin creates Bob via the admin endpoint, then we log in as Bob.
    create = await client.post(
        "/api/v1/admin/users",
        json={"username": "bob", "password": "bob-pw-1234"},
    )
    assert create.status_code == 201
    await client.post(
        "/api/v1/auth/login",
        json={"username": "bob", "password": "bob-pw-1234"},
    )

    # Bob can't see alice's entry.
    response = await client.get(f"/api/v1/entries/{alice_entry_id}")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ENTRY_NOT_FOUND"

    # Bob can't update alice's entry.
    response = await client.put(
        f"/api/v1/entries/{alice_entry_id}",
        json={"scripture_ref": "John 3:17"},
    )
    assert response.status_code == 404

    # Bob can't delete alice's entry.
    response = await client.delete(f"/api/v1/entries/{alice_entry_id}")
    assert response.status_code == 404

    # Bob's own list is empty.
    response = await client.get("/api/v1/entries")
    body = response.json()
    assert body["entries"] == []
    assert body["total"] == 0
    assert body["limit"] == 20
    assert body["offset"] == 0


# ---- create ----------------------------------------------------------------


async def test_create_minimal_payload(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    entry = await _create_entry(client, scripture_ref="John 3:16")

    assert entry["title"] is None
    assert entry["display_title"] == "John 3:16"
    assert entry["entry_date"] == date.today().isoformat()
    assert entry["scripture_ref"] == "John 3:16"
    assert entry["translation_code"] == "BSB"
    assert entry["scripture_text"].startswith("For God so loved the world")
    assert entry["observation"] == ""
    assert entry["application"] == ""
    assert entry["prayer"] == ""
    assert entry["tags"] == []


async def test_create_full_payload(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    entry = await _create_entry(
        client,
        title="On grace",
        entry_date="2026-01-15",
        scripture_ref="John 3:16-20",
        observation="The world is loved.",
        application="Trust Him.",
        prayer="Lord, increase my faith.",
        tags=["faith", "grace"],
    )
    assert entry["title"] == "On grace"
    assert entry["display_title"] == "On grace"
    assert entry["entry_date"] == "2026-01-15"
    assert entry["scripture_ref"] == "John 3:16-20"
    assert {t["name"] for t in entry["tags"]} == {"faith", "grace"}


async def test_create_normalizes_scripture_ref(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    entry = await _create_entry(client, scripture_ref="jn 3:16-20")
    assert entry["scripture_ref"] == "John 3:16-20"


async def test_create_whole_chapter_joins_all_verses(
    client: AsyncClient, bsb_loaded: None, db_session: AsyncSession
) -> None:
    await _register(client)
    entry = await _create_entry(client, scripture_ref="John 3")
    assert entry["scripture_ref"] == "John 3"
    # John 3 has 36 verses in the BSB.
    link_count = (
        await db_session.execute(
            select(func.count())
            .select_from(EntryScriptureVerse)
            .where(EntryScriptureVerse.entry_id == entry["id"])
        )
    ).scalar_one()
    assert link_count == 36
    # Joined text should be reasonably long.
    assert len(entry["scripture_text"]) > 500


async def test_create_bad_reference_returns_400(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.post("/api/v1/entries", json={"scripture_ref": "Frodo 3:16"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_REFERENCE"


async def test_create_out_of_range_reference_returns_404(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await client.post("/api/v1/entries", json={"scripture_ref": "John 3:99"})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "REFERENCE_OUT_OF_RANGE"


async def test_create_chapter_out_of_range_returns_404(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await client.post("/api/v1/entries", json={"scripture_ref": "John 99"})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "CHAPTER_NOT_FOUND"


async def test_create_unknown_translation_returns_404(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await client.post(
        "/api/v1/entries",
        json={"scripture_ref": "John 3:16", "translation_code": "NOPE"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "TRANSLATION_NOT_FOUND"


# ---- tag handling on create -----------------------------------------------


async def test_create_dedupes_tags_case_insensitively(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    entry = await _create_entry(client, scripture_ref="John 3:16", tags=["Faith", "FAITH", "faith"])
    assert len(entry["tags"]) == 1
    # Original casing of the first occurrence wins.
    assert entry["tags"][0]["name"] == "Faith"


async def test_create_reuses_existing_tag_case_insensitively(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    first = await _create_entry(client, scripture_ref="John 3:16", tags=["Faith"])
    second = await _create_entry(client, scripture_ref="John 3:17", tags=["faith"])
    assert first["tags"][0]["id"] == second["tags"][0]["id"]
    # Stored name keeps the casing from the first time it was created.
    assert second["tags"][0]["name"] == "Faith"


async def test_create_trims_tag_whitespace(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    entry = await _create_entry(client, scripture_ref="John 3:16", tags=["  hope  "])
    assert entry["tags"][0]["name"] == "hope"


async def test_create_rejects_empty_tag_after_trim(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.post(
        "/api/v1/entries",
        json={"scripture_ref": "John 3:16", "tags": ["   "]},
    )
    assert response.status_code == 422


async def test_create_rejects_tag_over_max_length(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.post(
        "/api/v1/entries",
        json={"scripture_ref": "John 3:16", "tags": ["x" * 51]},
    )
    assert response.status_code == 422


async def test_create_rejects_tag_with_control_chars(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.post(
        "/api/v1/entries",
        json={"scripture_ref": "John 3:16", "tags": ["bad\x00tag"]},
    )
    assert response.status_code == 422


# ---- read ------------------------------------------------------------------


async def test_get_entry_by_id_returns_full_payload(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    created = await _create_entry(client, scripture_ref="John 3:16", title="Hope", tags=["faith"])
    response = await client.get(f"/api/v1/entries/{created['id']}")
    assert response.status_code == 200
    body = response.json()["entry"]
    assert body["id"] == created["id"]
    assert body["title"] == "Hope"
    assert [t["name"] for t in body["tags"]] == ["faith"]


async def test_list_empty_for_new_user(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get("/api/v1/entries")
    assert response.status_code == 200
    body = response.json()
    assert body["entries"] == []
    assert body["total"] == 0
    assert body["limit"] == 20
    assert body["offset"] == 0


async def test_list_default_order_is_newest_first(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    today = date.today()
    older = (today - timedelta(days=5)).isoformat()
    newer = (today - timedelta(days=1)).isoformat()
    await _create_entry(client, scripture_ref="John 3:16", entry_date=older)
    await _create_entry(client, scripture_ref="John 3:17", entry_date=newer)

    body = (await client.get("/api/v1/entries")).json()
    assert body["total"] == 2
    dates = [e["entry_date"] for e in body["entries"]]
    assert dates == [newer, older]


async def test_list_oldest_order_reverses(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    today = date.today()
    older = (today - timedelta(days=5)).isoformat()
    newer = (today - timedelta(days=1)).isoformat()
    await _create_entry(client, scripture_ref="John 3:16", entry_date=older)
    await _create_entry(client, scripture_ref="John 3:17", entry_date=newer)

    body = (await client.get("/api/v1/entries?order=oldest")).json()
    dates = [e["entry_date"] for e in body["entries"]]
    assert dates == [older, newer]


async def test_list_paginates(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    base = date.today()
    for i in range(5):
        await _create_entry(
            client,
            scripture_ref=f"John 3:{16 + i}",
            entry_date=(base - timedelta(days=i)).isoformat(),
        )

    body = (await client.get("/api/v1/entries?limit=2&offset=0")).json()
    assert body["total"] == 5
    assert len(body["entries"]) == 2

    body = (await client.get("/api/v1/entries?limit=2&offset=2")).json()
    assert len(body["entries"]) == 2

    body = (await client.get("/api/v1/entries?limit=2&offset=4")).json()
    assert len(body["entries"]) == 1


async def test_list_limit_capped(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get("/api/v1/entries?limit=101")
    assert response.status_code == 422


# ---- update ----------------------------------------------------------------


async def test_update_replaces_all_fields(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    created = await _create_entry(
        client,
        title="First",
        scripture_ref="John 3:16",
        observation="o",
        application="a",
        prayer="p",
        tags=["faith"],
    )

    response = await client.put(
        f"/api/v1/entries/{created['id']}",
        json={"scripture_ref": "John 3:17"},  # everything else omitted
    )
    assert response.status_code == 200
    body = response.json()["entry"]
    assert body["title"] is None
    assert body["scripture_ref"] == "John 3:17"
    assert body["observation"] == ""
    assert body["application"] == ""
    assert body["prayer"] == ""
    assert body["tags"] == []


async def test_update_rebuilds_verse_links_on_ref_change(
    client: AsyncClient, bsb_loaded: None, db_session: AsyncSession
) -> None:
    await _register(client)
    created = await _create_entry(client, scripture_ref="John 3:16")
    entry_id = created["id"]
    initial_count = (
        await db_session.execute(
            select(func.count())
            .select_from(EntryScriptureVerse)
            .where(EntryScriptureVerse.entry_id == entry_id)
        )
    ).scalar_one()
    assert initial_count == 1

    response = await client.put(
        f"/api/v1/entries/{entry_id}",
        json={"scripture_ref": "John 3:16-20"},
    )
    assert response.status_code == 200
    new_count = (
        await db_session.execute(
            select(func.count())
            .select_from(EntryScriptureVerse)
            .where(EntryScriptureVerse.entry_id == entry_id)
        )
    ).scalar_one()
    assert new_count == 5
    # scripture_text grew with the range.
    assert len(response.json()["entry"]["scripture_text"]) > len(created["scripture_text"])


async def test_update_bumps_updated_at_but_not_created_at(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    created = await _create_entry(client, scripture_ref="John 3:16")
    original_created = created["created_at"]
    original_updated = created["updated_at"]

    # Ensure wall-clock advances past microsecond resolution.
    await asyncio.sleep(0.05)

    response = await client.put(
        f"/api/v1/entries/{created['id']}",
        json={"scripture_ref": "John 3:17"},
    )
    body = response.json()["entry"]
    assert body["created_at"] == original_created
    assert body["updated_at"] != original_updated


async def test_update_unknown_entry_returns_404(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.put("/api/v1/entries/9999", json={"scripture_ref": "John 3:16"})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ENTRY_NOT_FOUND"


# ---- delete ----------------------------------------------------------------


async def test_delete_removes_entry_and_link_rows(
    client: AsyncClient, bsb_loaded: None, db_session: AsyncSession
) -> None:
    await _register(client)
    created = await _create_entry(client, scripture_ref="John 3:16-20", tags=["faith"])
    entry_id = created["id"]

    response = await client.delete(f"/api/v1/entries/{entry_id}")
    assert response.status_code == 204

    # Entry gone.
    assert await db_session.get(Entry, entry_id) is None

    # Verse links gone.
    verse_count = (
        await db_session.execute(
            select(func.count())
            .select_from(EntryScriptureVerse)
            .where(EntryScriptureVerse.entry_id == entry_id)
        )
    ).scalar_one()
    assert verse_count == 0

    # Tag links gone.
    tag_link_count = (
        await db_session.execute(
            select(func.count()).select_from(EntryTag).where(EntryTag.entry_id == entry_id)
        )
    ).scalar_one()
    assert tag_link_count == 0


async def test_delete_keeps_orphaned_tag_for_user(
    client: AsyncClient, bsb_loaded: None, db_session: AsyncSession
) -> None:
    await _register(client)
    created = await _create_entry(client, scripture_ref="John 3:16", tags=["lonely"])
    await client.delete(f"/api/v1/entries/{created['id']}")

    # Orphaned tag still in DB.
    tag = (await db_session.execute(select(Tag).where(Tag.name == "lonely"))).scalar_one_or_none()
    assert tag is not None

    # Visible in /tags with entry_count=0.
    body = (await client.get("/api/v1/tags")).json()
    lonely = next(t for t in body["tags"] if t["name"] == "lonely")
    assert lonely["entry_count"] == 0


async def test_delete_unknown_entry_returns_404(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.delete("/api/v1/entries/9999")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ENTRY_NOT_FOUND"


# ---- verse linkage explicit ------------------------------------------------


async def test_verse_linkage_creates_exact_rows(
    client: AsyncClient, bsb_loaded: None, db_session: AsyncSession
) -> None:
    await _register(client)
    created = await _create_entry(client, scripture_ref="John 3:16-20")

    rows = (
        await db_session.execute(
            select(EntryScriptureVerse.verse_id).where(
                EntryScriptureVerse.entry_id == created["id"]
            )
        )
    ).all()
    assert len(rows) == 5
