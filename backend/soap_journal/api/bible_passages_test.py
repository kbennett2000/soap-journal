"""Tests for /api/v1/bible/passages/entries — passage to entries cross-refs."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient


async def _register(client: AsyncClient, username: str = "alice") -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "password123"},
    )
    assert response.status_code == 201, response.text


async def _create(
    client: AsyncClient,
    scripture_ref: str,
    *,
    title: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"scripture_ref": scripture_ref}
    if title is not None:
        payload["title"] = title
    response = await client.post("/api/v1/entries", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["entry"]


# ---- overlap semantics -----------------------------------------------------


async def test_overlapping_range_matches(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    await _create(client, "John 3:14-18", title="Bronze serpent + love")

    body = (await client.get("/api/v1/bible/passages/entries", params={"ref": "John 3:16"})).json()
    assert body["count"] == 1
    assert body["entries"][0]["title"] == "Bronze serpent + love"


async def test_left_overlap_matches(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    await _create(client, "John 3:16-20", title="Light entry")

    body = (await client.get("/api/v1/bible/passages/entries", params={"ref": "John 3:16"})).json()
    assert body["count"] == 1


async def test_whole_chapter_entry_matches_specific_verse_query(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    await _create(client, "John 3", title="Whole chapter")

    body = (await client.get("/api/v1/bible/passages/entries", params={"ref": "John 3:16"})).json()
    assert body["count"] == 1
    assert body["entries"][0]["title"] == "Whole chapter"


async def test_different_chapter_does_not_match(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    await _create(client, "John 4:1", title="Different chapter")

    body = (await client.get("/api/v1/bible/passages/entries", params={"ref": "John 3:16"})).json()
    assert body["count"] == 0
    assert body["entries"] == []


async def test_whole_chapter_query_returns_all_overlapping_entries(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    await _create(client, "John 3:16", title="One")
    await _create(client, "John 3:17-20", title="Two")
    await _create(client, "John 4:1", title="Different chapter")  # excluded

    body = (await client.get("/api/v1/bible/passages/entries", params={"ref": "John 3"})).json()
    titles = sorted(e["title"] for e in body["entries"])
    assert titles == ["One", "Two"]
    assert body["count"] == 2


async def test_no_matching_entries_returns_empty(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    await _create(client, "Romans 8:28", title="Far away")

    body = (await client.get("/api/v1/bible/passages/entries", params={"ref": "John 3:16"})).json()
    assert body["count"] == 0


# ---- reference resolution errors ------------------------------------------


async def test_bad_reference_returns_400(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get("/api/v1/bible/passages/entries", params={"ref": "Frodo 3:16"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_REFERENCE"


async def test_out_of_range_reference_returns_404(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get("/api/v1/bible/passages/entries", params={"ref": "John 3:99"})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "REFERENCE_OUT_OF_RANGE"


async def test_unknown_translation_returns_404(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get(
        "/api/v1/bible/passages/entries",
        params={"ref": "John 3:16", "translation": "NOPE"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "TRANSLATION_NOT_FOUND"


# ---- auth + isolation ------------------------------------------------------


async def test_unauthenticated_returns_401(client: AsyncClient, bsb_loaded: None) -> None:
    response = await client.get("/api/v1/bible/passages/entries", params={"ref": "John 3:16"})
    assert response.status_code == 401


async def test_other_users_entries_excluded(client: AsyncClient, bsb_loaded: None) -> None:
    # Alice creates a matching entry.
    await _register(client, "alice")
    await _create(client, "John 3:16", title="Alice's entry")

    # Admin creates Bob; log in as Bob.
    await client.post(
        "/api/v1/admin/users",
        json={"username": "bob", "password": "bob-pw-1234"},
    )
    await client.post(
        "/api/v1/auth/login",
        json={"username": "bob", "password": "bob-pw-1234"},
    )
    body = (await client.get("/api/v1/bible/passages/entries", params={"ref": "John 3:16"})).json()
    # Bob's view: no entries match because Alice's entry is hers.
    assert body["count"] == 0
    assert body["entries"] == []


# ---- query budget ----------------------------------------------------------


async def test_passage_entries_query_budget(client: AsyncClient, bsb_loaded: None, engine) -> None:
    """The endpoint runs at most 4 SELECTs against Bible/entry tables:
    translation; combined book+chapter+verses+chapter_count; entries
    (joined with translations.code); tags batched IN(...). See the
    endpoint docstring for the per-query mapping.
    """
    from sqlalchemy import event

    await _register(client)
    await _create(client, "John 3:16")

    queries: list[str] = []

    def _listen(conn, cursor, statement, parameters, context, executemany):
        normalized = " ".join(statement.split()).lower()
        if normalized.startswith("select"):
            queries.append(normalized)

    event.listen(engine.sync_engine, "before_cursor_execute", _listen)
    try:
        response = await client.get("/api/v1/bible/passages/entries", params={"ref": "John 3:16"})
        assert response.status_code == 200
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", _listen)

    # Count only queries that touch the Bible or entry tables — ignore
    # auth/session noise.
    relevant = [
        q
        for q in queries
        if any(
            substring in q
            for substring in (
                " translations",
                " books",
                " chapters",
                " verses",
                " entries",
                " entry_scripture_verses",
                " entry_tags",
                " tags",
            )
        )
    ]
    # 4 is the brief's stated budget; the endpoint hits it via a
    # LEFT-JOINed book+chapter+verses+chapter_count query.
    assert len(relevant) <= 4, f"too many queries: {len(relevant)} -> {relevant}"
