"""Tests for the journal backup export endpoint.

The strict key-set test is the load-bearing interop guarantee: the mobile
restore validates every object with Zod ``.strict()`` and rejects any unknown
key, so the export must emit ONLY the contract keys.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

import pytest
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


# ============================================================================
# POST /backup/import
# ============================================================================


async def _post_import(client: AsyncClient, payload, *, dry_run: bool = False):
    """POST a backup to the import endpoint. ``payload`` is a dict (JSON-encoded
    here) or raw bytes (sent verbatim, for malformed-JSON tests)."""
    url = "/api/v1/backup/import" + ("?dry_run=true" if dry_run else "")
    content = payload if isinstance(payload, bytes) else json.dumps(payload)
    return await client.post(url, content=content)


async def _login_as_new_user(client: AsyncClient, username: str, password: str) -> None:
    """Admin-create a user (the registered admin is logged in) and switch to it."""
    create = await client.post(
        "/api/v1/admin/users", json={"username": username, "password": password}
    )
    assert create.status_code == 201, create.text
    login = await client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert login.status_code == 200, login.text


async def _export(client: AsyncClient) -> dict:
    return (await client.get("/api/v1/backup/export")).json()


def _phone_entry(
    *,
    title: str | None,
    entry_date: str,
    scripture_ref: str,
    code: str,
    text: str,
    created_at: str,
    updated_at: str,
    verses: list[dict],
    tags: list[str],
) -> dict:
    """An entry shaped exactly like the mobile buildBackup output."""
    return {
        "title": title,
        "entry_date": entry_date,
        "scripture_ref": scripture_ref,
        "scripture_translation_code": code,
        "scripture_text": text,
        "observation": "obs",
        "application": "app",
        "prayer": "pray",
        "created_at": created_at,
        "updated_at": updated_at,
        "verses": verses,
        "tags": tags,
    }


def _doc(*entries: dict, exported_at: str = "2026-06-01T12:00:00.000Z") -> dict:
    return {
        "format": "soap-journal-backup",
        "version": 1,
        "exported_at": exported_at,
        "entries": list(entries),
    }


# Two BSB entries with phone-style millisecond "…Z" timestamps.
_ROMANS = _phone_entry(
    title="From phone",
    entry_date="2026-05-30",
    scripture_ref="Romans 8:28-30",
    code="BSB",
    text="And we know that God works all things together for good.",
    created_at="2026-05-30T08:00:00.000Z",
    updated_at="2026-05-30T08:05:00.000Z",
    verses=[
        {"book_order_index": 45, "chapter": 8, "verse": 28},
        {"book_order_index": 45, "chapter": 8, "verse": 29},
        {"book_order_index": 45, "chapter": 8, "verse": 30},
    ],
    tags=["faith", "grace"],
)
_JOHN = _phone_entry(
    title=None,
    entry_date="2026-05-31",
    scripture_ref="John 3:16",
    code="BSB",
    text="For God so loved the world.",
    created_at="2026-05-31T09:00:00.000Z",
    updated_at="2026-05-31T09:00:00.000Z",
    verses=[{"book_order_index": 43, "chapter": 3, "verse": 16}],
    tags=[],
)
# An entry in a translation that is NOT loaded on this server.
_ESV = _phone_entry(
    title="ESV one",
    entry_date="2026-05-29",
    scripture_ref="Psalm 23:1",
    code="ESV",
    text="The LORD is my shepherd.",
    created_at="2026-05-29T07:00:00.000Z",
    updated_at="2026-05-29T07:00:00.000Z",
    verses=[{"book_order_index": 19, "chapter": 23, "verse": 1}],
    tags=["psalm"],
)


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# ---- auth gating -----------------------------------------------------------


async def test_import_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await _post_import(client, _doc(_JOHN))
    assert response.status_code == 401


# ---- happy path ------------------------------------------------------------


async def test_import_happy_path_inserts_and_is_queryable(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await _post_import(client, _doc(_ROMANS, _JOHN))
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["inserted"] == 2
    assert report["updated"] == 0
    assert report["skipped_missing_translation"] == 0
    assert report["total_in_file"] == 2

    entries = {e["scripture_ref"]: e for e in (await _export(client))["entries"]}
    romans = entries["Romans 8:28-30"]
    assert romans["title"] == "From phone"
    assert romans["entry_date"] == "2026-05-30"
    assert romans["scripture_text"].startswith("And we know")
    assert romans["tags"] == ["faith", "grace"]
    assert [[v["book_order_index"], v["chapter"], v["verse"]] for v in romans["verses"]] == [
        [45, 8, 28],
        [45, 8, 29],
        [45, 8, 30],
    ]
    # Timestamps preserved (instant equal; phone's ".000Z" normalizes to "Z").
    assert _instant(romans["created_at"]) == _instant("2026-05-30T08:00:00.000Z")
    assert _instant(romans["updated_at"]) == _instant("2026-05-30T08:05:00.000Z")
    assert entries["John 3:16"]["title"] is None


# ---- cross-app round-trip (headline) ---------------------------------------


async def test_import_cross_app_roundtrip_with_missing_translation(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await _post_import(client, _doc(_ROMANS, _JOHN, _ESV))
    assert response.status_code == 200, response.text
    report = response.json()

    # The two BSB entries import; the ESV entry is skipped + reported; no abort.
    assert report["inserted"] == 2
    assert report["skipped_missing_translation"] == 1
    assert report["missing_translations"] == ["ESV"]
    assert report["total_in_file"] == 3

    refs = {e["scripture_ref"] for e in (await _export(client))["entries"]}
    assert refs == {"Romans 8:28-30", "John 3:16"}  # Psalm 23:1 (ESV) did not land


# ---- dry run ---------------------------------------------------------------


async def test_import_dry_run_reports_but_commits_nothing(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await _post_import(client, _doc(_ROMANS, _JOHN), dry_run=True)
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["dry_run"] is True
    assert report["inserted"] == 2  # counts as if applied

    assert (await _export(client))["entries"] == []  # nothing committed


# ---- idempotency over HTTP -------------------------------------------------


async def test_import_idempotent_over_http(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    first = (await _post_import(client, _doc(_ROMANS, _JOHN))).json()
    assert first["inserted"] == 2

    second = (await _post_import(client, _doc(_ROMANS, _JOHN))).json()
    assert second["inserted"] == 0
    assert second["updated"] == 0
    assert second["skipped_unchanged"] == 2

    refs = [e["scripture_ref"] for e in (await _export(client))["entries"]]
    assert sorted(refs) == ["John 3:16", "Romans 8:28-30"]  # no duplicates


# ---- multi-user ------------------------------------------------------------


async def test_import_lands_under_current_user_only(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client, "alice")
    await _create_entry(client, scripture_ref="John 3:16", title="alice-entry")

    await _login_as_new_user(client, "bob", "bob-pw-1234")
    report = (await _post_import(client, _doc(_ROMANS))).json()
    assert report["inserted"] == 1
    bob_refs = {e["scripture_ref"] for e in (await _export(client))["entries"]}
    assert bob_refs == {"Romans 8:28-30"}

    # Alice's journal is untouched.
    await client.post(
        "/api/v1/auth/login", json={"username": "alice", "password": "password123"}
    )
    alice = (await _export(client))["entries"]
    assert [e["title"] for e in alice] == ["alice-entry"]


# ---- validate-before-write (each leaves the DB unchanged) ------------------


def _with_extra_key(doc: dict) -> dict:
    bad = json.loads(json.dumps(doc))
    bad["entries"][0]["id"] = 7  # an unknown key the phone would never send
    return bad


def _with_bad_format(doc: dict) -> dict:
    bad = json.loads(json.dumps(doc))
    bad["format"] = "not-a-soap-journal-backup"
    return bad


def _with_bad_timestamp(doc: dict) -> dict:
    bad = json.loads(json.dumps(doc))
    bad["entries"][0]["created_at"] = "not-a-timestamp"
    return bad


def _with_bad_entry_date(doc: dict) -> dict:
    bad = json.loads(json.dumps(doc))
    bad["entries"][0]["entry_date"] = "2026-13-99"
    return bad


@pytest.mark.parametrize(
    ("make_payload", "expected_code"),
    [
        (lambda: b"{not valid json", "INVALID_BACKUP"),
        (lambda: _with_extra_key(_doc(_JOHN)), "INVALID_BACKUP"),
        (lambda: _with_bad_format(_doc(_JOHN)), "INVALID_BACKUP"),
        (lambda: _with_bad_timestamp(_doc(_JOHN)), "INVALID_BACKUP"),
        (lambda: _with_bad_entry_date(_doc(_JOHN)), "INVALID_BACKUP"),
    ],
)
async def test_import_rejects_bad_files_without_writing(
    client: AsyncClient, bsb_loaded: None, make_payload, expected_code: str
) -> None:
    await _register(client)
    await _create_entry(client, scripture_ref="John 3:16", title="pre-existing")

    response = await _post_import(client, make_payload())
    assert response.status_code == 400, response.text
    assert response.json()["detail"]["code"] == expected_code

    # DB unchanged: the pre-existing entry is still the only one.
    entries = (await _export(client))["entries"]
    assert [e["title"] for e in entries] == ["pre-existing"]


async def test_import_newer_version_is_friendly_400(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    payload = _doc(_JOHN)
    payload["version"] = 2
    response = await _post_import(client, payload)
    assert response.status_code == 400, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "BACKUP_VERSION_UNSUPPORTED"
    assert "newer version" in detail["message"]
