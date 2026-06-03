"""Tests for the journal backup export endpoint.

The strict key-set test is the load-bearing interop guarantee: the mobile
restore validates every object with Zod ``.strict()`` and rejects any unknown
key, so the export must emit ONLY the contract keys.
"""

from __future__ import annotations

import re

from httpx import AsyncClient

# The contract key sets (see schemas/backup.py / the mobile Zod schema).
TOP_LEVEL_KEYS = {"format", "version", "exported_at", "entries"}
ENTRY_KEYS = {
    "title",
    "entry_date",
    "scripture_ref",
    "scripture_translation_code",
    "scripture_text",
    "observation",
    "application",
    "prayer",
    "created_at",
    "updated_at",
    "verses",
    "tags",
}
VERSE_KEYS = {"book_order_index", "chapter", "verse"}

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


# ---- auth gating -----------------------------------------------------------


async def test_export_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/backup/export")
    assert response.status_code == 401


# ---- strict interop --------------------------------------------------------


async def test_export_emits_exactly_the_contract_keys(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    await _create_entry(client, scripture_ref="Romans 8:28-30", tags=["faith"])

    body = (await client.get("/api/v1/backup/export")).json()

    # No extra top-level keys (e.g. no id leaking through).
    assert set(body) == TOP_LEVEL_KEYS
    assert body["format"] == "soap-journal-backup"
    assert body["version"] == 1

    for entry in body["entries"]:
        # Exactly the 12 contract keys — proves no id/user_id/display_title.
        assert set(entry) == ENTRY_KEYS
        for verse in entry["verses"]:
            assert set(verse) == VERSE_KEYS


async def test_export_field_names_and_values(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    await _create_entry(client, scripture_ref="Romans 8:28-30", tags=["faith", "Grace"])

    body = (await client.get("/api/v1/backup/export")).json()
    entry = body["entries"][0]

    # The file field is scripture_translation_code, not translation_code.
    assert entry["scripture_translation_code"] == "BSB"
    assert entry["scripture_ref"] == "Romans 8:28-30"
    # Verse coordinate uses book_order_index (Romans = 45), ordered.
    assert [[v["book_order_index"], v["chapter"], v["verse"]] for v in entry["verses"]] == [
        [45, 8, 28],
        [45, 8, 29],
        [45, 8, 30],
    ]
    # Tag names, original casing, ordered by lower(name).
    assert entry["tags"] == ["faith", "Grace"]


async def test_export_empty_journal(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    body = (await client.get("/api/v1/backup/export")).json()
    assert set(body) == TOP_LEVEL_KEYS
    assert body["entries"] == []
    assert body["exported_at"].endswith("Z")


# ---- download framing ------------------------------------------------------


async def test_export_download_headers(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get("/api/v1/backup/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert re.fullmatch(
        r'attachment; filename="soap-journal-backup-\d{4}-\d{2}-\d{2}\.json"',
        response.headers["content-disposition"],
    )


# ---- multi-user isolation --------------------------------------------------


async def test_export_never_includes_other_users_entries(
    client: AsyncClient, bsb_loaded: None
) -> None:
    # Alice (first user → admin) creates an entry.
    await _register(client, "alice")
    await _create_entry(client, scripture_ref="John 3:16", title="alice-entry")

    # Admin provisions Bob, then we log in as Bob (switches the session cookie).
    create = await client.post(
        "/api/v1/admin/users",
        json={"username": "bob", "password": "bob-pw-1234"},
    )
    assert create.status_code == 201
    await client.post(
        "/api/v1/auth/login",
        json={"username": "bob", "password": "bob-pw-1234"},
    )
    await _create_entry(client, scripture_ref="John 3:17", title="bob-entry")

    # Bob's export contains only Bob's entry.
    bob_body = (await client.get("/api/v1/backup/export")).json()
    assert [e["title"] for e in bob_body["entries"]] == ["bob-entry"]

    # Back to Alice — her export contains only her entry.
    await client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "password123"},
    )
    alice_body = (await client.get("/api/v1/backup/export")).json()
    assert [e["title"] for e in alice_body["entries"]] == ["alice-entry"]
