"""Tests for the per-user tag list + autocomplete endpoints."""

from __future__ import annotations

from httpx import AsyncClient


async def _register(client: AsyncClient, username: str = "alice") -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "password123"},
    )
    assert response.status_code == 201, response.text


async def _make_entry(
    client: AsyncClient, scripture_ref: str, tags: list[str]
) -> dict:
    response = await client.post(
        "/api/v1/entries",
        json={"scripture_ref": scripture_ref, "tags": tags},
    )
    assert response.status_code == 201, response.text
    return response.json()["entry"]


# ---- auth gating -----------------------------------------------------------


async def test_tags_list_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tags")
    assert response.status_code == 401


async def test_tags_autocomplete_unauthenticated_returns_401(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/tags/autocomplete?q=fa")
    assert response.status_code == 401


# ---- list ------------------------------------------------------------------


async def test_tag_list_returns_empty_for_new_user(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    body = (await client.get("/api/v1/tags")).json()
    assert body == {"tags": []}


async def test_tag_list_counts_match_reality(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    await _make_entry(client, "John 3:16", ["faith", "grace"])
    await _make_entry(client, "John 3:17", ["faith", "hope"])

    body = (await client.get("/api/v1/tags")).json()
    counts = {t["name"]: t["entry_count"] for t in body["tags"]}
    assert counts == {"faith": 2, "grace": 1, "hope": 1}


async def test_tag_list_ordered_alphabetically_case_insensitive(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    await _make_entry(client, "John 3:16", ["zebra"])
    await _make_entry(client, "John 3:17", ["Apple"])
    await _make_entry(client, "John 3:18", ["mountain"])

    body = (await client.get("/api/v1/tags")).json()
    names = [t["name"] for t in body["tags"]]
    assert names == ["Apple", "mountain", "zebra"]


async def test_tag_list_scoped_to_user(
    client: AsyncClient, bsb_loaded: None
) -> None:
    # Alice creates an entry with the tag "faith".
    await _register(client, "alice")
    await _make_entry(client, "John 3:16", ["faith"])

    # Admin creates Bob; we log in as Bob.
    create = await client.post(
        "/api/v1/admin/users",
        json={"username": "bob", "password": "bob-pw-1234"},
    )
    assert create.status_code == 201
    await client.post(
        "/api/v1/auth/login",
        json={"username": "bob", "password": "bob-pw-1234"},
    )
    # Bob makes his own entry with the same tag name.
    await _make_entry(client, "John 3:17", ["faith"])

    bob_body = (await client.get("/api/v1/tags")).json()
    assert len(bob_body["tags"]) == 1
    # Bob's tag has count 1, not 2 — alice's tag is a different row.
    assert bob_body["tags"][0]["entry_count"] == 1


# ---- autocomplete ----------------------------------------------------------


async def test_autocomplete_orders_by_entry_count_desc(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    await _make_entry(client, "John 3:16", ["family"])  # 1
    await _make_entry(client, "John 3:17", ["faith"])  # 1
    await _make_entry(client, "John 3:18", ["faith"])  # 2

    body = (await client.get("/api/v1/tags/autocomplete?q=fa")).json()
    names = [t["name"] for t in body["tags"]]
    counts = [t["entry_count"] for t in body["tags"]]
    assert names == ["faith", "family"]
    assert counts == [2, 1]


async def test_autocomplete_case_insensitive_query(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    await _make_entry(client, "John 3:16", ["Faith"])

    body = (await client.get("/api/v1/tags/autocomplete?q=FA")).json()
    assert len(body["tags"]) == 1
    assert body["tags"][0]["name"] == "Faith"


async def test_autocomplete_returns_only_prefix_matches(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    await _make_entry(client, "John 3:16", ["faith"])
    await _make_entry(client, "John 3:17", ["unfailing"])

    body = (await client.get("/api/v1/tags/autocomplete?q=fa")).json()
    names = [t["name"] for t in body["tags"]]
    assert names == ["faith"]


async def test_autocomplete_caps_at_10(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    for i in range(15):
        await _make_entry(client, f"John 3:{16 + (i % 5)}", [f"foo-{i:02d}"])

    body = (await client.get("/api/v1/tags/autocomplete?q=foo")).json()
    assert len(body["tags"]) == 10


async def test_autocomplete_missing_q_returns_422(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await client.get("/api/v1/tags/autocomplete")
    assert response.status_code == 422


async def test_autocomplete_empty_q_returns_422(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await client.get("/api/v1/tags/autocomplete?q=")
    assert response.status_code == 422


async def test_autocomplete_whitespace_only_q_returns_422(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await client.get("/api/v1/tags/autocomplete?q=%20%20%20")
    assert response.status_code == 422
