"""Tests for the FTS5 bible search endpoint (ADR-0003 Cycle 2).

Fixture-based and fast: a small canonical translation (the mini fixture from
load_translation_test) is loaded into the per-test transaction, which the
`client` shares, so the endpoint searches it. No real-PDF parse.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, text

from soap_journal.cli.load_translation import load_canonical_translation
from soap_journal.cli.load_translation_test import _full_translation
from soap_journal.db.models.book import Book
from soap_journal.db.models.chapter import Chapter
from soap_journal.db.models.cross_reference import CrossReference
from soap_journal.db.models.footnote import Footnote
from soap_journal.db.models.heading import Heading
from soap_journal.db.models.translation import Translation
from soap_journal.db.models.verse import Verse

SEARCH = "/api/v1/bible/search"


async def _reset_bible(db_session) -> None:
    """Clear all bible data (incl. committed BSB and the FTS tables) within the
    per-test transaction. ALL-mode search spans every translation, so these
    tests need a slate containing only their own fixtures; the session-scoped
    BSB is restored on teardown rollback."""
    for model in (CrossReference, Footnote, Heading, Verse, Chapter, Book, Translation):
        await db_session.execute(delete(model))
    await db_session.execute(text("DELETE FROM verses_fts"))
    await db_session.execute(text("DELETE FROM notes_fts"))
    await db_session.flush()


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


# ---- translation=ALL grouped mode (Cycle 3) --------------------------------


async def test_all_groups_shared_verse_into_one_row(client: AsyncClient, db_session) -> None:
    await _register(client)
    await _reset_bible(db_session)
    await _load(db_session, code="AAA", enrich_notes=True)
    await _load(db_session, code="BBB", enrich_notes=True)

    # "Exodus 1:1" exists in both AAA and BBB: ALL collapses it to ONE row whose
    # translation_codes lists both — and total counts distinct verses, not the 2
    # raw FTS matches.
    body = (
        await client.get(SEARCH, params={"q": "exodus", "translation": "ALL", "scope": "verses"})
    ).json()
    assert body["translation_code"] == "ALL"
    assert len(body["verse_hits"]) == 1
    hit = body["verse_hits"][0]
    assert _ref(hit) == ("Exod", 1, 1)
    assert hit["translation_codes"] == ["AAA", "BBB"]
    assert "<mark>" in hit["snippet"]
    assert body["total_verse_hits"] == 1


async def test_all_singleton_verse_returns_one_row(client: AsyncClient, db_session) -> None:
    await _register(client)
    await _reset_bible(db_session)
    await _load(db_session, code="AAA", enrich_notes=True)  # Genesis 1:1-5
    await _load(db_session, code="CCC")  # plain: Genesis 1:1 only, no "5" anywhere

    # The token "5" occurs only in AAA's "Gen 1:5".
    body = (
        await client.get(SEARCH, params={"q": "5", "translation": "ALL", "scope": "verses"})
    ).json()
    assert body["total_verse_hits"] == 1
    assert len(body["verse_hits"]) == 1
    hit = body["verse_hits"][0]
    assert _ref(hit) == ("Gen", 1, 5)
    assert hit["translation_codes"] == ["AAA"]


async def test_all_pagination_over_groups(client: AsyncClient, db_session) -> None:
    await _register(client)
    await _reset_bible(db_session)
    await _load(db_session, code="AAA", enrich_notes=True)
    await _load(db_session, code="BBB", enrich_notes=True)

    base = {"q": "1", "translation": "ALL", "scope": "verses", "limit": 2}
    p0 = (await client.get(SEARCH, params={**base, "offset": 0})).json()
    p1 = (await client.get(SEARCH, params={**base, "offset": 2})).json()

    assert len(p0["verse_hits"]) == 2
    assert len(p1["verse_hits"]) == 2
    assert p0["total_verse_hits"] == p1["total_verse_hits"] >= 4
    page0 = {_ref(h) for h in p0["verse_hits"]}
    page1 = {_ref(h) for h in p1["verse_hits"]}
    assert page0.isdisjoint(page1)  # non-overlapping grouped pages
    # Every shared verse lists both translations.
    assert all(h["translation_codes"] == ["AAA", "BBB"] for h in p0["verse_hits"])


async def test_all_ordering_is_stable(client: AsyncClient, db_session) -> None:
    await _register(client)
    await _reset_bible(db_session)
    await _load(db_session, code="AAA", enrich_notes=True)
    await _load(db_session, code="BBB", enrich_notes=True)

    params = {"q": "1", "translation": "ALL", "scope": "verses", "limit": 10}
    first = [_ref(h) for h in (await client.get(SEARCH, params=params)).json()["verse_hits"]]
    second = [_ref(h) for h in (await client.get(SEARCH, params=params)).json()["verse_hits"]]
    assert first == second  # deterministic tie-break (canonical order)


async def test_all_notes_are_flat_not_grouped(client: AsyncClient, db_session) -> None:
    await _register(client)
    await _reset_bible(db_session)
    await _load(db_session, code="AAA", enrich_notes=True)
    await _load(db_session, code="BBB", enrich_notes=True)

    # "hebrew" matches the tn note in both translations AND the verse "Hebrews
    # 1:1" in both. Verses group to one row; notes stay flat (one per source).
    body = (
        await client.get(SEARCH, params={"q": "hebrew", "translation": "ALL", "scope": "both"})
    ).json()
    heb = [h for h in body["verse_hits"] if _ref(h) == ("Heb", 1, 1)]
    assert len(heb) == 1
    assert heb[0]["translation_codes"] == ["AAA", "BBB"]
    assert len(body["note_hits"]) == 2
    assert {n["translation_code"] for n in body["note_hits"]} == {"AAA", "BBB"}
    assert all(n["note_type"] == "tn" for n in body["note_hits"])


async def test_all_scope_notes_only_returns_flat_notes(client: AsyncClient, db_session) -> None:
    await _register(client)
    await _reset_bible(db_session)
    await _load(db_session, code="AAA", enrich_notes=True)

    body = (
        await client.get(SEARCH, params={"q": "hebrew", "translation": "ALL", "scope": "notes"})
    ).json()
    assert body["translation_code"] == "ALL"
    assert body["verse_hits"] == []
    assert len(body["note_hits"]) == 1
    assert body["note_hits"][0]["translation_code"] == "AAA"


async def test_single_translation_path_unchanged_no_regression(
    client: AsyncClient, db_session
) -> None:
    await _register(client)
    await _load(db_session, code="TST", enrich_notes=True)

    body = (
        await client.get(SEARCH, params={"q": "exodus", "translation": "TST", "scope": "verses"})
    ).json()
    assert body["translation_code"] == "TST"
    assert len(body["verse_hits"]) == 1
    hit = body["verse_hits"][0]
    assert hit["translation_code"] == "TST"
    assert hit["translation_codes"] is None  # single mode leaves the group list unset
