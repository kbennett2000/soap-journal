"""Tests for the Bible reader API.

Strategy: the `bsb_loaded` session-scoped fixture in conftest.py loads the
real bundled BSB once for the whole test session. Each test still gets a
function-scoped per-test transaction that rolls back, so test writes
(e.g. user registration to obtain a cookie) don't leak across tests, but
the BSB data persists. Using real BSB keeps the tests honest about
chapter counts (Psalms 150, John 21, Revelation 22), omitted-verse
handling, and book-boundary navigation.
"""

from __future__ import annotations

import urllib.parse

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from soap_journal.db.models.book import Book
from soap_journal.db.models.chapter import Chapter
from soap_journal.db.models.footnote import Footnote
from soap_journal.db.models.heading import Heading
from soap_journal.db.models.translation import Translation
from soap_journal.db.models.verse import Verse
from soap_journal.parsers.bsb import OMITTED_VERSE_PLACEHOLDER

# ---- helpers ---------------------------------------------------------------


async def _register(client: AsyncClient, username: str = "alice") -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "password123"},
    )
    assert response.status_code == 201, response.text


def _encode_path(part: str) -> str:
    """URL-encode a path segment so it survives book names like 'Song of Solomon'
    and 'Psalm' (no spaces to encode) or '1 Cor'."""
    return urllib.parse.quote(part, safe="")


def _chapter_url(code: str, book: str, chapter: int) -> str:
    return f"/api/v1/bible/translations/{code}/books/{_encode_path(book)}/chapters/{chapter}"


async def _drop_all_bible_data(db_session) -> None:
    """Empty every Bible-related table for the duration of the current test
    transaction. The session-scoped bsb_loaded fixture commits BSB to the
    shared in-memory DB; tests that need an "empty DB" state delete inside
    their own transaction (rolled back at teardown so other tests still see
    BSB).
    """
    for model in (Footnote, Heading, Verse, Chapter, Book, Translation):
        await db_session.execute(delete(model))
    await db_session.flush()


# ---- auth gating -----------------------------------------------------------


async def test_translations_list_unauthenticated_returns_401(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/bible/translations")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "NOT_AUTHENTICATED"


async def test_chapter_endpoint_unauthenticated_returns_401(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/bible/translations/BSB/books/John/chapters/3")
    assert response.status_code == 401


async def test_resolve_endpoint_unauthenticated_returns_401(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/bible/resolve?ref=John%203:16")
    assert response.status_code == 401


async def test_authenticated_non_admin_can_read_bible(
    client: AsyncClient, bsb_loaded: None
) -> None:
    # Alice (first user) is admin; create a second non-admin user via the
    # admin endpoint and log in as her.
    await _register(client, "alice")
    create = await client.post(
        "/api/v1/admin/users",
        json={"username": "bob", "password": "bob-pw-1234"},
    )
    assert create.status_code == 201
    await client.post(
        "/api/v1/auth/login",
        json={"username": "bob", "password": "bob-pw-1234"},
    )

    response = await client.get("/api/v1/bible/translations")
    assert response.status_code == 200
    assert response.json()["translations"][0]["code"] == "BSB"


# ---- translations list -----------------------------------------------------


async def test_list_translations_returns_bsb_when_loaded(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await client.get("/api/v1/bible/translations")
    assert response.status_code == 200
    body = response.json()
    assert len(body["translations"]) == 1
    t = body["translations"][0]
    assert t["code"] == "BSB"
    assert t["name"] == "Berean Standard Bible"
    assert t["language"] == "en"
    assert "public domain" in t["copyright"].lower()


async def test_list_translations_empty_when_nothing_loaded(
    client: AsyncClient, bsb_loaded: None, db_session
) -> None:
    await _register(client)
    await _drop_all_bible_data(db_session)
    response = await client.get("/api/v1/bible/translations")
    assert response.status_code == 200
    assert response.json() == {"translations": []}


# ---- translation detail ----------------------------------------------------


async def test_translation_detail_returns_66_books_in_canonical_order(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await client.get("/api/v1/bible/translations/BSB")
    assert response.status_code == 200
    body = response.json()
    assert body["translation"]["code"] == "BSB"
    assert len(body["books"]) == 66
    order = [b["order_index"] for b in body["books"]]
    assert order == list(range(1, 67))
    assert body["books"][0]["name"] == "Genesis"
    assert body["books"][-1]["name"] == "Revelation"


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Genesis", 50),
        ("Psalms", 150),
        ("John", 21),
        ("Revelation", 22),
        ("Jude", 1),
    ],
)
async def test_translation_detail_chapter_counts_match(
    client: AsyncClient, bsb_loaded: None, name: str, expected: int
) -> None:
    await _register(client)
    response = await client.get("/api/v1/bible/translations/BSB")
    body = response.json()
    book = next(b for b in body["books"] if b["name"] == name)
    assert book["chapter_count"] == expected


async def test_translation_detail_testament_split(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    body = (await client.get("/api/v1/bible/translations/BSB")).json()
    ot = [b for b in body["books"] if b["testament"] == "OT"]
    nt = [b for b in body["books"] if b["testament"] == "NT"]
    assert len(ot) == 39
    assert len(nt) == 27


async def test_translation_detail_unknown_code_returns_404(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await client.get("/api/v1/bible/translations/NOPE")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "TRANSLATION_NOT_FOUND"


async def test_translation_detail_uses_single_chapter_count_query(
    client: AsyncClient, bsb_loaded: None, engine
) -> None:
    """Verify the chapter-count query for the detail endpoint is grouped,
    not N+1 (one per book = 66 queries). Mechanism: a SQLAlchemy
    `before_cursor_execute` event listener counts SELECTs against `chapters`
    while the endpoint runs.
    """
    from sqlalchemy import event

    chapter_count_queries: list[str] = []

    def _listen(conn, cursor, statement, parameters, context, executemany):
        # Count any SELECT that hits the chapters table — that's the
        # query whose duplication would mean N+1.
        normalized = " ".join(statement.split())
        if normalized.lower().startswith("select") and " chapters" in normalized.lower():
            chapter_count_queries.append(normalized)

    event.listen(engine.sync_engine, "before_cursor_execute", _listen)
    try:
        await _register(client)
        response = await client.get("/api/v1/bible/translations/BSB")
        assert response.status_code == 200
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", _listen)

    # One grouped query joining books to chapters is expected. 66 would
    # mean N+1.
    assert len(chapter_count_queries) == 1, (
        f"expected exactly 1 chapter-table query, got {len(chapter_count_queries)}: "
        f"{chapter_count_queries[:3]}"
    )


# ---- chapter retrieval -----------------------------------------------------


async def test_chapter_john_3_returns_36_verses(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get(
        f"/api/v1/bible/translations/BSB/books/{_encode_path('John')}/chapters/3"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["chapter_number"] == 3
    assert body["book"]["name"] == "John"
    assert len(body["verses"]) == 36
    verse_16 = next(v for v in body["verses"] if v["number"] == 16)
    assert verse_16["text"].startswith("For God so loved the world")


async def test_chapter_no_red_letters_in_bsb(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    body = (
        await client.get(f"/api/v1/bible/translations/BSB/books/{_encode_path('John')}/chapters/3")
    ).json()
    assert all(v["is_red_letter"] is False for v in body["verses"])


async def test_chapter_bsb_has_no_headings_or_footnotes(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    body = (
        await client.get(f"/api/v1/bible/translations/BSB/books/{_encode_path('John')}/chapters/3")
    ).json()
    assert body["headings"] == []
    assert all(v["footnotes"] == [] for v in body["verses"])


async def test_chapter_with_omitted_verse_keeps_slot_with_placeholder(
    client: AsyncClient, bsb_loaded: None
) -> None:
    # Acts 8:37 is one of the 16 verses absent from the modern critical
    # text — the BSB ships it empty and the parser substitutes the
    # OMITTED_VERSE_PLACEHOLDER constant.
    await _register(client)
    body = (
        await client.get(f"/api/v1/bible/translations/BSB/books/{_encode_path('Acts')}/chapters/8")
    ).json()
    verse_37 = next(v for v in body["verses"] if v["number"] == 37)
    assert verse_37["text"] == OMITTED_VERSE_PLACEHOLDER


async def test_chapter_resolves_by_abbreviation(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get(
        f"/api/v1/bible/translations/BSB/books/{_encode_path('Jn')}/chapters/3"
    )
    assert response.status_code == 200
    assert response.json()["book"]["name"] == "John"


async def test_chapter_resolves_by_alias(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get(
        f"/api/v1/bible/translations/BSB/books/{_encode_path('Apocalypse')}/chapters/22"
    )
    assert response.status_code == 200
    assert response.json()["book"]["name"] == "Revelation"


async def test_chapter_navigation_within_book(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    body = (
        await client.get(f"/api/v1/bible/translations/BSB/books/{_encode_path('John')}/chapters/3")
    ).json()
    assert body["previous"] == {"book_name": "John", "chapter_number": 2}
    assert body["next"] == {"book_name": "John", "chapter_number": 4}


async def test_chapter_navigation_crosses_book_boundary_forward(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    body = (
        await client.get(f"/api/v1/bible/translations/BSB/books/{_encode_path('John')}/chapters/21")
    ).json()
    assert body["next"] == {"book_name": "Acts", "chapter_number": 1}


async def test_chapter_navigation_crosses_book_boundary_backward(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    body = (
        await client.get(f"/api/v1/bible/translations/BSB/books/{_encode_path('Acts')}/chapters/1")
    ).json()
    assert body["previous"] == {"book_name": "John", "chapter_number": 21}


async def test_chapter_navigation_first_chapter_genesis_has_null_previous(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    body = (
        await client.get(
            f"/api/v1/bible/translations/BSB/books/{_encode_path('Genesis')}/chapters/1"
        )
    ).json()
    assert body["previous"] is None
    assert body["next"] == {"book_name": "Genesis", "chapter_number": 2}


async def test_chapter_navigation_last_chapter_revelation_has_null_next(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    body = (
        await client.get(
            f"/api/v1/bible/translations/BSB/books/{_encode_path('Revelation')}/chapters/22"
        )
    ).json()
    assert body["next"] is None
    assert body["previous"] == {"book_name": "Revelation", "chapter_number": 21}


async def test_chapter_unknown_translation_404(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get(
        f"/api/v1/bible/translations/NOPE/books/{_encode_path('John')}/chapters/3"
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "TRANSLATION_NOT_FOUND"


async def test_chapter_unknown_book_404(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get(
        f"/api/v1/bible/translations/BSB/books/{_encode_path('Frodo')}/chapters/1"
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "BOOK_NOT_FOUND"


async def test_chapter_zero_returns_404(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get(
        f"/api/v1/bible/translations/BSB/books/{_encode_path('John')}/chapters/0"
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "CHAPTER_NOT_FOUND"


async def test_chapter_past_end_returns_404(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get(
        f"/api/v1/bible/translations/BSB/books/{_encode_path('John')}/chapters/99"
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "CHAPTER_NOT_FOUND"


# ---- reference resolve -----------------------------------------------------


async def test_resolve_single_verse(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get(
        "/api/v1/bible/resolve",
        params={"ref": "John 3:16", "translation": "BSB"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reference"]["canonical_string"] == "John 3:16"
    assert body["reference"]["translation_code"] == "BSB"
    assert body["reference"]["start_verse"] == 16
    assert body["reference"]["end_verse"] == 16
    assert len(body["verses"]) == 1
    assert body["verses"][0]["text"].startswith("For God so loved the world")


async def test_resolve_verse_range(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get("/api/v1/bible/resolve", params={"ref": "John 3:16-20"})
    assert response.status_code == 200
    body = response.json()
    assert body["reference"]["canonical_string"] == "John 3:16-20"
    assert [v["number"] for v in body["verses"]] == [16, 17, 18, 19, 20]


async def test_resolve_whole_chapter_fills_start_and_end(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await client.get("/api/v1/bible/resolve", params={"ref": "John 3"})
    assert response.status_code == 200
    body = response.json()
    assert body["reference"]["canonical_string"] == "John 3"
    assert body["reference"]["start_verse"] == 1
    assert body["reference"]["end_verse"] == 36
    assert len(body["verses"]) == 36


async def test_resolve_normalizes_alias_to_canonical(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get("/api/v1/bible/resolve", params={"ref": "jn 3:16"})
    assert response.json()["reference"]["canonical_string"] == "John 3:16"


async def test_resolve_handles_no_space_numbered_book(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await client.get("/api/v1/bible/resolve", params={"ref": "1Cor 13"})
    assert response.status_code == 200
    body = response.json()
    assert body["reference"]["canonical_string"] == "1 Corinthians 13"
    assert len(body["verses"]) == 13  # BSB count for 1 Cor 13


async def test_resolve_accepts_en_dash(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get("/api/v1/bible/resolve", params={"ref": "John 3:16–20"})
    assert response.status_code == 200
    assert response.json()["reference"]["canonical_string"] == "John 3:16-20"


async def test_resolve_verse_out_of_range_returns_404(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await client.get("/api/v1/bible/resolve", params={"ref": "John 3:99"})
    assert response.status_code == 404
    body = response.json()
    assert body["detail"]["code"] == "REFERENCE_OUT_OF_RANGE"
    assert "36" in body["detail"]["message"]  # actual chapter length


async def test_resolve_chapter_out_of_range_returns_404(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await client.get("/api/v1/bible/resolve", params={"ref": "John 99"})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "CHAPTER_NOT_FOUND"


async def test_resolve_unknown_book_returns_400_invalid_reference(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await client.get("/api/v1/bible/resolve", params={"ref": "Frodo 3:16"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_REFERENCE"


async def test_resolve_cross_chapter_range_returns_400(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await client.get("/api/v1/bible/resolve", params={"ref": "John 3:30-4:2"})
    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["code"] == "INVALID_REFERENCE"
    assert "cross-chapter" in body["detail"]["message"]


async def test_resolve_missing_ref_param_returns_422(client: AsyncClient, bsb_loaded: None) -> None:
    await _register(client)
    response = await client.get("/api/v1/bible/resolve")
    assert response.status_code == 422


async def test_resolve_defaults_to_first_loaded_translation(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await client.get("/api/v1/bible/resolve", params={"ref": "John 3:16"})
    assert response.status_code == 200
    assert response.json()["reference"]["translation_code"] == "BSB"


async def test_resolve_unknown_translation_returns_404(
    client: AsyncClient, bsb_loaded: None
) -> None:
    await _register(client)
    response = await client.get(
        "/api/v1/bible/resolve",
        params={"ref": "John 3:16", "translation": "NOPE"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "TRANSLATION_NOT_FOUND"


async def test_resolve_with_no_translations_loaded_returns_404(
    client: AsyncClient, bsb_loaded: None, db_session
) -> None:
    # Clear in-transaction so the default-translation lookup has nothing
    # to return. The session-scoped BSB load is restored on test teardown.
    await _register(client)
    await _drop_all_bible_data(db_session)
    response = await client.get("/api/v1/bible/resolve", params={"ref": "John 3:16"})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "TRANSLATION_NOT_FOUND"


# ---- notes + cross-references (ADR-0002) ------------------------------------
#
# Load a small notes-bearing translation into the per-test transaction (the
# `client` shares this session, so the endpoints see it; it rolls back at
# teardown). The mini fixture's Genesis 1 carries a plain footnote on v2 and a
# typed, char-anchored note on v3 whose cross-ref points at John 1:1 in the
# same translation. The full parse is NOT exercised — this stays fast and lives
# in the default suite.


async def _load_translation(
    db_session, *, enrich_notes: bool = False, enrich_genesis: bool = False
) -> None:
    from soap_journal.cli.load_translation import load_canonical_translation
    from soap_journal.cli.load_translation_test import _full_translation

    payload = _full_translation(
        code="NETT", name="NET-ish Test", enrich_notes=enrich_notes, enrich_genesis=enrich_genesis
    )
    await load_canonical_translation(db_session, payload)
    await db_session.flush()


async def test_chapter_includes_typed_notes_and_resolved_cross_refs(
    client: AsyncClient, bsb_loaded: None, db_session
) -> None:
    await _register(client)
    await _load_translation(db_session, enrich_notes=True)

    body = (await client.get(_chapter_url("NETT", "Genesis", 1))).json()

    verse_3 = next(v for v in body["verses"] if v["number"] == 3)
    assert len(verse_3["footnotes"]) == 1
    note = verse_3["footnotes"][0]
    assert note["note_type"] == "tn"
    assert note["char_offset"] == 4
    assert note["marker"] == 1
    assert note["ordinal"] == 0
    assert note["text"].startswith("tn ")
    # Cross-ref resolved to the target book's abbreviation within this translation.
    assert note["cross_refs"] == [
        {"to_book": "John", "to_chapter": 1, "to_verse_start": 1, "to_verse_end": None}
    ]


async def test_chapter_plain_footnote_has_null_note_fields(
    client: AsyncClient, bsb_loaded: None, db_session
) -> None:
    # Backward-compat for the 13 plain translations: a plain footnote (no type)
    # serializes with null note fields, ordinal 0, and no cross-refs.
    await _register(client)
    await _load_translation(db_session, enrich_genesis=True)  # plain footnote on Gen 1:2

    body = (await client.get(_chapter_url("NETT", "Genesis", 1))).json()

    verse_2 = next(v for v in body["verses"] if v["number"] == 2)
    assert len(verse_2["footnotes"]) == 1
    note = verse_2["footnotes"][0]
    assert note["note_type"] is None
    assert note["char_offset"] is None
    assert note["marker"] is None
    assert note["ordinal"] == 0
    assert note["cross_refs"] == []


async def test_bsb_chapter_footnote_shape_unchanged(client: AsyncClient, bsb_loaded: None) -> None:
    # The bundled BSB has no footnotes; the enriched payload must still serve it
    # unchanged (empty footnote lists), proving the additive fields are safe.
    await _register(client)
    body = (
        await client.get(f"/api/v1/bible/translations/BSB/books/{_encode_path('John')}/chapters/3")
    ).json()
    assert all(v["footnotes"] == [] for v in body["verses"])


async def test_resolve_includes_typed_notes_and_cross_refs(
    client: AsyncClient, bsb_loaded: None, db_session
) -> None:
    # The resolve endpoint shares _verses_with_footnotes, so it gets the same
    # enriched verses.
    await _register(client)
    await _load_translation(db_session, enrich_notes=True)

    body = (
        await client.get(
            "/api/v1/bible/resolve", params={"ref": "Genesis 1:3", "translation": "NETT"}
        )
    ).json()
    assert len(body["verses"]) == 1
    note = body["verses"][0]["footnotes"][0]
    assert note["note_type"] == "tn"
    assert note["cross_refs"][0]["to_book"] == "John"


async def test_chapter_notes_query_count_is_fixed_no_n_plus_one(
    client: AsyncClient, bsb_loaded: None, db_session, engine
) -> None:
    """The chapter endpoint issues a fixed number of footnote/cross-ref queries
    regardless of how many verses/notes the chapter has — not one per verse or
    per footnote. Counts SELECTs against the footnotes and cross_references
    tables via a before_cursor_execute listener.
    """
    from sqlalchemy import event

    await _register(client)
    await _load_translation(db_session, enrich_notes=True)

    footnote_queries: list[str] = []
    xref_queries: list[str] = []

    def _listen(conn, cursor, statement, parameters, context, executemany):
        normalized = " ".join(statement.split()).lower()
        if normalized.startswith("select") and " footnotes" in normalized:
            footnote_queries.append(normalized)
        if normalized.startswith("select") and " cross_references" in normalized:
            xref_queries.append(normalized)

    event.listen(engine.sync_engine, "before_cursor_execute", _listen)
    try:
        response = await client.get(_chapter_url("NETT", "Genesis", 1))
        assert response.status_code == 200
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", _listen)

    # Exactly one footnotes query and one cross_references query for the whole
    # chapter (Genesis 1 has 5 verses and 2 footnotes here).
    assert len(footnote_queries) == 1, footnote_queries
    assert len(xref_queries) == 1, xref_queries
