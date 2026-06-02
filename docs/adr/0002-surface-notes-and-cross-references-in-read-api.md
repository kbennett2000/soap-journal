# ADR 0002 — Surface translator's notes and cross-references in the read API

**Status:** Accepted

**Date:** 2026-06-02

## Context

ADR-0001 gave the data model typed, character-anchored footnotes (`note_type`,
`char_offset`, `marker`, `ordinal`) and a `cross_references` table, and the NET Bible is
loaded with ~58k notes and ~16k cross-references. But the read API still drops all of it: the
chapter and reference endpoints return `FootnoteResponse{id, text}` only, so the reader
client cannot show note types or cross-reference links. This ADR surfaces that data through
the read API, without breaking the 13 plain public-domain translations (which have
`note_type = NULL` and no cross-references). FTS/search over verses + notes is a **separate
later cycle**, not part of this one.

## Decision

**1 — Inline, not a separate endpoint.** Enrich `FootnoteResponse` in place and nest
cross-references under each footnote, delivered in the existing chapter (`GET
/translations/{code}/books/{book}/chapters/{n}`) and reference (`GET /resolve`) payloads — no
second round-trip. Footnotes are already nested under verses here, so this is the natural
extension and matches the NET app's proven shape. Rejected: a separate `/notes` endpoint
(an extra call and an extra client-side join for no benefit).

**2 — Additive and backward compatible; no migration.** New response fields only:
`FootnoteResponse` gains `note_type`, `char_offset`, `marker`, `ordinal`, and a `cross_refs`
list; a new `CrossRefResponse` is introduced. The 13 plain translations return
`note_type=null`, `char_offset=null`, `marker=null`, `ordinal=0`, `cross_refs=[]`; the client
branches on `note_type`. The DB columns and `cross_references` table already exist (migration
`4708ebfdc41a`), so this is purely read-side — **no Alembic migration** and `alembic heads`
is unchanged.

**3 — Query shape: fixed query count, no N+1.** Extend the shared `_verses_with_footnotes`
helper (which feeds *both* the chapter and resolve endpoints) to a fixed set of queries:
(1) verses by `chapter_id`; (2) footnotes by `verse_id IN (...)` ordered by
`(verse_id, ordinal, id)`; (3) — only when the chapter has footnotes — cross-refs by
`footnote_id IN (...)` joined once to `books` for the target abbreviation, ordered by `id`.
Cross-refs are grouped by `footnote_id`, then footnotes by `verse_id`, in Python (the pattern
the helper already uses). The per-chapter query count is constant regardless of how many
verses/notes/cross-refs the chapter has.

**4 — Cross-reference shape.** `CrossRefResponse{to_book, to_chapter, to_verse_start,
to_verse_end}`, where `to_book` is the target book's **abbreviation**, resolved from
`cross_references.to_book_id` within the same translation. The abbreviation is both a display
label ("John 1:3", "1 Cor 8:6") and a navigable alias — `get_book_by_name` and the chapter
route accept abbreviations — so one field serves render and click-through. Targets were
resolved into the same translation at load time, so resolution is a plain join.

## Consequences

- The reader client gets typed notes + cross-reference links in one payload; the 13 plain
  translations are unaffected (defaulted nulls/empties).
- One extra query per chapter when footnotes exist; still O(1) in chapter size.
- `CrossRefResponse.to_book` is an abbreviation, not a full name; a client wanting the full
  name resolves it (the alias table already maps abbreviations to canonical names).
- Out of scope (future): FTS/search over verses + notes; the frontend rendering of note
  types and cross-reference links.
