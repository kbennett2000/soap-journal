# ADR 0003 — Full-text search over verses and translator's notes

**Status:** Accepted

**Date:** 2026-06-02

## Context

The reader can display verses and NET translator's notes (ADR-0001/0002), but nothing can
search scripture or notes. The NET app had FTS5 over a single, read-only `bible.db`
(`verses_fts` + `notes_fts`, `porter unicode61`, populated once at ingest, no triggers). This
app differs in one way the NET app never faced: **14 translations load and replace through the
loader, and the same verse exists in all of them**, so the design must decide search scope and
dedup across translations. The existing entry keyword search (`core/entries_query.py`, LIKE
over a user's private journal) is a separate feature over separate data and is untouched.

This ADR is implemented in cycles; **Cycle 1 (this change) is schema + loader only** — no
search endpoint yet (Cycle 2).

## Decisions

**1 — Scope model.** Search a **single translation by default** (`?translation=<code>`,
mirroring the reader; defaults to the first-loaded translation). Opt-in `?translation=ALL`
searches every loaded translation but **groups verse hits by canonical `(book order_index,
chapter, verse)`** → one row per verse carrying the matched translation codes and best-ranked
snippet, so a verse doesn't appear 14×. *(Endpoint behavior lands in Cycles 2–3; the schema
below supports both.)*

**2 — What's searchable.** Verse text and footnote bodies, kept as separate result lists.
Substantial notes exist only for NET, so note results are, in practice, NET-dominated; the
result contract surfaces each note hit's translation code rather than hard-filtering.

**3 — FTS sync: loader-managed, standalone tables (not external-content).**
- `verses_fts(text, translation_id UNINDEXED)`, rowid = `verses.id`
- `notes_fts(body, translation_id UNINDEXED, note_type UNINDEXED)`, rowid = `footnotes.id`
- tokenizer `porter unicode61` (matches the NET app).

*Standalone over external-content* because per-translation load/replace needs cheap teardown:
a standalone FTS5 table supports `DELETE FROM verses_fts WHERE translation_id = ?`, whereas an
external-content table requires the per-row special `('delete', rowid, <old values>)` command —
awkward for a 31k-verse bulk replace. The duplicated text is modest for a self-hosted SQLite
app. `translation_id` (UNINDEXED) powers both single-scope filtering and teardown; `note_type`
(UNINDEXED) lets a note hit report its type without a join.

The loader populates both tables in `_insert_translation` (one bulk `INSERT … SELECT` per
table, scoped to the new translation, after its rows are flushed) and tears them down **first**
in `_delete_existing_translation` (`DELETE … WHERE translation_id = ?`, ahead of the
footnote/verse deletes) so a replace never orphans FTS rows. Loader-managed (no triggers)
matches the existing explicit dependency-ordered delete and keeps writes in one place.

**4 — Migration + DDL hook, with backfill.** FTS5 virtual tables aren't ORM-mapped, so the
`CREATE VIRTUAL TABLE` / `DROP` SQL lives once in `db/fts.py` and is attached to
`Base.metadata` via `event.listen(..., "after_create"/"before_drop", DDL(...))`. This is
load-bearing: the **test DB is built by `Base.metadata.create_all`**, not migrations, so
without the hook the tables wouldn't exist in tests. The Alembic migration runs the **same**
SQL constants (imported from `db/fts.py`, so the two paths can't drift) for real DBs, and
**backfills** `verses_fts`/`notes_fts` from existing `verses`/`footnotes` rows. The backfill is
mandatory: the 13 bundled translations are already loaded in real databases and predate these
tables — without it, search would silently return nothing for them until a manual reload.
`down_revision` chains off head `4708ebfdc41a`; heads advance by exactly one.

## Consequences

- Search works immediately after `alembic upgrade` on an already-populated DB (backfill), and
  stays correct across translation load/replace (loader populate + teardown-first).
- FTS index roughly doubles the stored verse/note text — acceptable for this scale.
- Cross-translation dedup is handled in the query layer (Cycle 3), not the schema.
- **Out of scope:** the search endpoint/ranking/snippets (Cycle 2–3); FTS over journal
  entries (entry search stays LIKE-based); the frontend search UI.
