"""Tests for the annotations (highlights) CRUD API."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from soap_journal.db.models.annotation import Annotation


async def _register(client: AsyncClient, username: str = "alice") -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "password123"},
    )
    assert response.status_code == 201, response.text


def _body(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "translation_code": "NET",
        "book": "John",
        "chapter": 3,
        "verse_start": 16,
        "verse_end": 16,
        "char_start": 0,
        "char_end": 5,
        "color": "yellow",
        "note": None,
    }
    base.update(overrides)
    return base


async def _create(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    response = await client.post("/api/v1/annotations", json=_body(**overrides))
    assert response.status_code == 201, response.text
    return response.json()["annotation"]


# ---- model invariant -------------------------------------------------------


def test_annotation_table_has_no_fk_to_verses_or_translations() -> None:
    # The reload-safety property: only user_id is a real FK. Canonical coords +
    # translation_code are FK-free so a translation reload can't orphan rows.
    referenced = {fk.column.table.name for fk in Annotation.__table__.foreign_keys}
    assert referenced == {"users"}


# ---- CRUD ------------------------------------------------------------------


async def test_crud_round_trip(client: AsyncClient) -> None:
    await _register(client)

    created = await _create(client, note="first thought")
    assert created["color"] == "yellow"
    assert created["note"] == "first thought"
    assert created["book"] == "John"
    annotation_id = created["id"]

    listed = (await client.get("/api/v1/annotations")).json()["annotations"]
    assert [a["id"] for a in listed] == [annotation_id]

    patched = await client.patch(
        f"/api/v1/annotations/{annotation_id}",
        json={"color": "green", "note": "revised"},
    )
    assert patched.status_code == 200
    body = patched.json()["annotation"]
    assert body["color"] == "green"
    assert body["note"] == "revised"

    # PATCH is partial: omitting note leaves it; sending null clears it.
    only_color = (
        await client.patch(f"/api/v1/annotations/{annotation_id}", json={"color": "blue"})
    ).json()["annotation"]
    assert only_color["color"] == "blue"
    assert only_color["note"] == "revised"
    cleared = (
        await client.patch(f"/api/v1/annotations/{annotation_id}", json={"note": None})
    ).json()["annotation"]
    assert cleared["note"] is None

    deleted = await client.delete(f"/api/v1/annotations/{annotation_id}")
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/annotations")).json()["annotations"] == []


async def test_create_normalizes_book_alias_to_canonical(client: AsyncClient) -> None:
    await _register(client)
    created = await _create(client, book="Jn")  # alias
    assert created["book"] == "John"
    # And it's findable by the canonical name filter.
    listed = (await client.get("/api/v1/annotations", params={"book": "John"})).json()
    assert len(listed["annotations"]) == 1


# ---- ownership -------------------------------------------------------------


async def test_user_cannot_touch_another_users_annotation(client: AsyncClient) -> None:
    await _register(client, "alice")
    alice = await _create(client)
    alice_id = alice["id"]

    # Admin (alice) creates bob, then we log in as bob.
    create = await client.post(
        "/api/v1/admin/users",
        json={"username": "bob", "password": "bob-pw-1234"},
    )
    assert create.status_code == 201
    await client.post(
        "/api/v1/auth/login",
        json={"username": "bob", "password": "bob-pw-1234"},
    )

    # Bob's list doesn't include alice's annotation.
    assert (await client.get("/api/v1/annotations")).json()["annotations"] == []
    # Bob can't update or delete it (404, not 403 — no existence leak).
    assert (
        await client.patch(f"/api/v1/annotations/{alice_id}", json={"color": "pink"})
    ).status_code == 404
    assert (await client.delete(f"/api/v1/annotations/{alice_id}")).status_code == 404


# ---- list filtering (the reader's per-chapter fetch) -----------------------


async def test_list_filters_by_translation_book_chapter(client: AsyncClient) -> None:
    await _register(client)
    net_john3 = await _create(client, translation_code="NET", book="John", chapter=3)
    await _create(client, translation_code="KJV", book="John", chapter=3)
    await _create(client, translation_code="NET", book="Genesis", chapter=1)

    # Reader fetch for NET / John / 3.
    res = (
        await client.get(
            "/api/v1/annotations",
            params={"translation": "NET", "book": "John", "chapter": 3},
        )
    ).json()["annotations"]
    assert [a["id"] for a in res] == [net_john3["id"]]

    # NET highlights don't show when listing KJV.
    kjv = (await client.get("/api/v1/annotations", params={"translation": "KJV"})).json()[
        "annotations"
    ]
    assert {a["translation_code"] for a in kjv} == {"KJV"}


# ---- validation ------------------------------------------------------------


async def test_rejects_verse_end_before_verse_start(client: AsyncClient) -> None:
    await _register(client)
    response = await client.post("/api/v1/annotations", json=_body(verse_start=16, verse_end=15))
    assert response.status_code == 422


async def test_rejects_color_outside_palette(client: AsyncClient) -> None:
    await _register(client)
    response = await client.post("/api/v1/annotations", json=_body(color="teal"))
    assert response.status_code == 422


async def test_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/annotations")
    assert response.status_code == 401
