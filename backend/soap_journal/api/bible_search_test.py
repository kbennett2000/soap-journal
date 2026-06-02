"""Tests for the FTS5 bible search endpoint (ADR-0003 Cycle 2).

Fixture-based and fast: a small canonical translation (the mini fixture from
load_translation_test) is loaded into the per-test transaction, which the
`client` shares, so the endpoint searches it. No real-PDF parse.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from soap_journal.cli.load_translation import load_canonical_translation
from soap_journal.cli.load_translation_test import _full_translation

SEARCH = "/api/v1/bible/search"


async def _register(client: AsyncClient, username: str = "alice") -> None:
    r = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "password123"},
    )
    assert r.status_code == 201, r.text


async def _load(
    db_session,
    *,
    code: str = "TST",
    enrich_notes: bool = False,
) -> None:
    await load_canonical_translation(
        db_session, _full_translation(code=code, enrich_notes=enrich_notes)
    )
    await db_session.flush()


def _ref(hit: dict) -> tuple[str, int, int]:
    return (hit["book"], hit["chapter"], hit["verse"])


# ---- auth ------------------------------------------------------------------


async def test_search_requires_auth(client: AsyncClient) -> None:
    r = await client.get(SEARCH, params={"q": "god"})
    assert r.status_code == 401


# ---- scopes ----------------------------------------------------------------


async def test_verse_scope_returns_highlighted_hit(client: AsyncClient, db_session) -> None:
    await _register(client)
    await _load(db_session, enrich_notes=True)

    r = await client.get(SEARCH, params={"q": "exodus", "translation": "TST", "scope": "verses"})
    assert r.status_code == 200
    body = r.json()
    assert body["scope"] == "verses"
    assert body["translation_code"] == "TST"
    assert len(body["verse_hits"]) == 1
    hit = body["verse_hits"][0]
    assert hit["book"] == "Exod"
    assert (hit["chapter"], hit["verse"]) == (1, 1)
    assert "<mark>" in hit["snippet"]
    assert hit["translation_code"] == "TST"
    assert body["note_hits"] == []
    assert body["total_verse_hits"] == 1


async def test_note_scope_returns_note_with_type(client: AsyncClient, db_session) -> None:
    await _register(client)
    await _load(db_session, enrich_notes=True)

    r = await client.get(SEARCH, params={"q": "hebrew", "translation": "TST", "scope": "notes"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["note_hits"]) == 1
    note = body["note_hits"][0]
    assert note["note_type"] == "tn"
    assert _ref(note) == ("Gen", 1, 3)
    assert "<mark>" in note["snippet"]
    assert body["verse_hits"] == []
    assert body["total_note_hits"] == 1


async def test_both_scope_returns_both_lists(client: AsyncClient, db_session) -> None:
    await _register(client)
    await _load(db_session, enrich_notes=True)

    # "hebrew" matches BOTH the tn note body ("...the Hebrew term...") and the
    # verse "Hebrews 1:1" (the porter stemmer maps Hebrews -> hebrew), so
    # scope=both populates both lists from one request.
    both = (
        await client.get(SEARCH, params={"q": "hebrew", "scope": "both", "translation": "TST"})
    ).json()
    assert len(both["note_hits"]) == 1
    assert both["note_hits"][0]["note_type"] == "tn"
    assert len(both["verse_hits"]) >= 1
    assert ("Heb", 1, 1) in {_ref(h) for h in both["verse_hits"]}

    # scope=notes restricts to the note list (no verse query runs).
    notes_only = (
        await client.get(SEARCH, params={"q": "hebrew", "scope": "notes", "translation": "TST"})
    ).json()
    assert notes_only["verse_hits"] == []
    assert len(notes_only["note_hits"]) == 1


# ---- plain translation (no notes) ------------------------------------------


async def test_plain_translation_notes_empty_not_error(client: AsyncClient, db_session) -> None:
    await _register(client)
    await _load(db_session, code="PLN")  # no footnotes at all

    r = await client.get(SEARCH, params={"q": "exodus", "translation": "PLN", "scope": "both"})
    assert r.status_code == 200
    body = r.json()
    assert body["note_hits"] == []
    assert body["total_note_hits"] == 0
    assert len(body["verse_hits"]) == 1  # verse search still works


# ---- translation resolution ------------------------------------------------


async def test_explicit_translation_does_not_leak(client: AsyncClient, db_session) -> None:
    await _register(client)
    await _load(db_session, code="AAA", enrich_notes=True)
    await _load(db_session, code="BBB", enrich_notes=True)

    # Both translations have an "Exodus 1:1" verse; filtering by AAA returns only
    # AAA's hit, not BBB's.
    r = await client.get(SEARCH, params={"q": "exodus", "translation": "AAA", "scope": "verses"})
    body = r.json()
    assert body["total_verse_hits"] == 1
    assert all(h["translation_code"] == "AAA" for h in body["verse_hits"])


async def test_translation_defaults_to_first_loaded(
    client: AsyncClient, bsb_loaded: None, db_session
) -> None:
    await _register(client)
    # No ?translation= → the first-loaded translation (BSB) is searched.
    r = await client.get(SEARCH, params={"q": "god", "scope": "verses"})
    assert r.status_code == 200
    body = r.json()
    assert body["translation_code"] == "BSB"
    assert len(body["verse_hits"]) > 0


# ---- query sanitisation safety ---------------------------------------------


@pytest.mark.parametrize("q", ['"', "*", "(test)", "a NEAR b", 'foo"', "tn:", ")("])
async def test_odd_queries_never_error(client: AsyncClient, db_session, q: str) -> None:
    await _register(client)
    await _load(db_session, enrich_notes=True)
    r = await client.get(SEARCH, params={"q": q, "translation": "TST"})
    # Odd/operator-laden input degrades to safe (often empty) results, never 500.
    assert r.status_code == 200


# ---- pagination ------------------------------------------------------------


async def test_pagination_returns_distinct_pages(client: AsyncClient, db_session) -> None:
    await _register(client)
    await _load(db_session, enrich_notes=True)

    # The digit "1" appears in most verse texts ("Exodus 1:1", ...), giving
    # enough matches to page.
    base = {"q": "1", "translation": "TST", "scope": "verses", "limit": 2}
    p0 = (await client.get(SEARCH, params={**base, "offset": 0})).json()
    p1 = (await client.get(SEARCH, params={**base, "offset": 2})).json()

    assert len(p0["verse_hits"]) == 2
    assert len(p1["verse_hits"]) == 2
    assert p0["total_verse_hits"] == p1["total_verse_hits"] >= 4
    page0 = {_ref(h) for h in p0["verse_hits"]}
    page1 = {_ref(h) for h in p1["verse_hits"]}
    assert page0.isdisjoint(page1)
