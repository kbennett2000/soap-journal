"""FTS5 full-text-search virtual tables for verses and notes.

These are SQLite FTS5 virtual tables, not ORM-mapped models, so they can't be
created by SQLAlchemy's table reflection. Instead the `CREATE`/`DROP` SQL lives
here as constants and is attached to `Base.metadata` via `after_create` /
`before_drop` DDL events — that's what makes the tables exist in the test
database (built by `Base.metadata.create_all`, not by migrations). The Alembic
migration imports these same constants so the migrated (real) DB and the
create_all (test) DB get byte-identical table definitions.

Design (see docs/adr/0003-full-text-search.md):
- Standalone tables (NOT `content=` external-content), so per-translation
  load/replace can tear rows down with `DELETE ... WHERE translation_id = ?`.
- `verses_fts(text, translation_id UNINDEXED)`, rowid = verses.id
- `notes_fts(body, translation_id UNINDEXED, note_type UNINDEXED)`, rowid = footnotes.id
- tokenizer `porter unicode61` (matches the NET app: English stemming + Unicode).

Row population/teardown is loader-managed in `cli/load_translation.py`; the
migration additionally backfills existing rows (the bundled translations
predate these tables).
"""

from __future__ import annotations

from sqlalchemy import DDL, event

from soap_journal.db.base import Base

# ---- table definitions (single source of truth, shared with the migration) ----

VERSES_FTS_CREATE = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS verses_fts "
    "USING fts5(text, translation_id UNINDEXED, tokenize = 'porter unicode61')"
)
NOTES_FTS_CREATE = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts "
    "USING fts5(body, translation_id UNINDEXED, note_type UNINDEXED, "
    "tokenize = 'porter unicode61')"
)
VERSES_FTS_DROP = "DROP TABLE IF EXISTS verses_fts"
NOTES_FTS_DROP = "DROP TABLE IF EXISTS notes_fts"

# ---- backfill (migration + tests): populate from ALL existing rows -----------
# rowid mirrors the source primary key so search results join straight back to
# verses/footnotes. Used by the migration to make pre-existing translations
# searchable without a manual reload.

BACKFILL_VERSES_FTS = (
    "INSERT INTO verses_fts (rowid, text, translation_id) "
    "SELECT v.id, v.text, b.translation_id "
    "FROM verses v "
    "JOIN chapters c ON c.id = v.chapter_id "
    "JOIN books b ON b.id = c.book_id"
)
BACKFILL_NOTES_FTS = (
    "INSERT INTO notes_fts (rowid, body, translation_id, note_type) "
    "SELECT f.id, f.text, b.translation_id, f.note_type "
    "FROM footnotes f "
    "JOIN verses v ON v.id = f.verse_id "
    "JOIN chapters c ON c.id = v.chapter_id "
    "JOIN books b ON b.id = c.book_id"
)

# ---- per-translation population/teardown (loader) ----------------------------
# Scoped by translation id. The loader binds :tid.

POPULATE_VERSES_FTS_FOR_TRANSLATION = (
    "INSERT INTO verses_fts (rowid, text, translation_id) "
    "SELECT v.id, v.text, :tid "
    "FROM verses v "
    "JOIN chapters c ON c.id = v.chapter_id "
    "JOIN books b ON b.id = c.book_id "
    "WHERE b.translation_id = :tid"
)
POPULATE_NOTES_FTS_FOR_TRANSLATION = (
    "INSERT INTO notes_fts (rowid, body, translation_id, note_type) "
    "SELECT f.id, f.text, :tid, f.note_type "
    "FROM footnotes f "
    "JOIN verses v ON v.id = f.verse_id "
    "JOIN chapters c ON c.id = v.chapter_id "
    "JOIN books b ON b.id = c.book_id "
    "WHERE b.translation_id = :tid"
)
DELETE_VERSES_FTS_FOR_TRANSLATION = "DELETE FROM verses_fts WHERE translation_id = :tid"
DELETE_NOTES_FTS_FOR_TRANSLATION = "DELETE FROM notes_fts WHERE translation_id = :tid"


# ---- create/drop hooks on Base.metadata (test DB via create_all) -------------
# `after_create` fires once the regular tables exist; the FTS tables are
# standalone so ordering only matters for drop (drop FTS before base tables).

event.listen(Base.metadata, "after_create", DDL(VERSES_FTS_CREATE))
event.listen(Base.metadata, "after_create", DDL(NOTES_FTS_CREATE))
event.listen(Base.metadata, "before_drop", DDL(VERSES_FTS_DROP))
event.listen(Base.metadata, "before_drop", DDL(NOTES_FTS_DROP))
