# ADR 0001 — Unify the Bible/notes data model to carry typed, word-anchored notes and cross-references

**Status:** Accepted

**Date:** 2026-06-02

## Context

We are evolving `soap-journal` to absorb the **NET Bible** as a user-supplied translation
(gitignored `bibles/net.pdf`, exactly like ESV/NKJV/NLT — the repo ships no copyrighted
text). NET is distinctive: it carries tens of thousands of rich translator's notes. Each
note is **typed** (`tn` translator, `sn` study, `tc` text-critical, `map`), **anchored to a
character offset** inside a verse, and may contain **cross-references** to other verses.

Today the canonical format (`backend/soap_journal/parsers/schema.py`) and the DB
(`footnotes` table) carry only `(verse_number, text)` footnotes — no type, no anchor, no
cross-references. The schema header explicitly deferred "inline footnote markers" and
"cross-references between verses." Meanwhile the 13 bundled public-domain translations
already validate and load against the frozen v1 schema.

Core tension: enrich the single canonical format and the DB to represent NET's note
richness **without** breaking the bundled translations or forcing a re-parse of them.

A NET parser already exists in the private repo `kbennett2000/net-bible-study`. It will be
**ported** (not rewritten) in a later cycle. We mine it only for the notes data model; its
architecture (single-translation raw-sqlite3 + SvelteKit) is discarded in favor of this
app's multi-translation SQLAlchemy + React.

### The NET source shape (verified against the private repo)

`backend/ingest/parser.py`:

```python
@dataclass
class CrossRefData:
    to_book_short: str            # book ABBREVIATION string, e.g. "Ps", "1 Cor"
    to_chapter: int
    to_verse_start: int
    to_verse_end: int | None = None   # None => single verse

@dataclass
class NoteRow:
    verse_number: int
    chapter: int
    marker: int                   # per-PAGE ordinal, 1-indexed (PDF-extraction artifact)
    word_offset: int              # *** char offset into the assembled verse text *** (misnamed)
    type: NoteType                # Literal["tn","sn","tc","map"]
    body: str                     # the note text
    ordinal: int                  # order WITHIN the verse, 0-indexed
    cross_refs: list[CrossRefData] = field(default_factory=list)
```

`docs/DESIGN.md` §0–2 confirm: `word_offset` is a **character** offset into `verse.text`
(the field name is misleading); `marker` is a per-page reading-order ordinal used only to
match in-text markers to note bodies during PDF extraction ("page" has no meaning in the
canonical format); `ordinal` is the 0-indexed render order of notes within a verse
(multiple notes per verse are possible); a cross-ref target is a book + chapter + verse
**range**, never a single resolved verse row (the private DB stores `to_chapter`/
`to_verse_start` as plain ints).

## Decision

Enrich the **existing footnote model** additively — one note concept, one table — rather
than introducing a parallel `notes` concept or an opaque JSON blob.

### Canonical schema (`parsers/schema.py`)

All additions are optional/defaulted so existing canonical JSON validates unchanged.

- New `CanonicalCrossRef`: `to_book_order_index: int` (1..66), `to_chapter: int` (≥1),
  `to_verse_start: int` (≥1), `to_verse_end: int | None = None`, with a validator that
  `to_verse_end >= to_verse_start` when present.
- Enrich `CanonicalFootnote` (which now models "a note, typed or untyped"):
  - `note_type: Literal["tn","sn","tc","map"] | None = None` — `None` = an untyped
    footnote (all 13 bundled translations).
  - `char_offset: int | None = None` (≥0) — character offset into the verse text. (NET's
    `word_offset` is mapped to this accurately-named field by the parser adapter.)
  - `marker: int | None = None` — page-relative provenance only; nothing depends on it.
  - `ordinal: int | None = None` — stable render order within the verse.
  - `cross_refs: list[CanonicalCrossRef] = []`.
- A new chapter-level validator: `char_offset`, when present, must be `<= len(verse.text)`
  for the referenced verse. Cross-ref **target existence is not validated at schema level**
  (targets span books absent from a single chapter); only `to_book_order_index ∈ 1..66`
  and the range invariant are enforced statically. Target-verse resolution is a load-time /
  read-time concern.

### Database (`db/models/`, one Alembic migration)

- Add nullable columns to `footnotes`: `note_type` (with a `CHECK` constraint limiting it to
  `tn/sn/tc/map`), `char_offset`, `marker`, `ordinal`. Bundled rows leave these NULL.
- New `cross_references` table: `id` PK; `footnote_id` FK → `footnotes.id`
  `ON DELETE CASCADE` (indexed); `to_book_id` FK → `books.id` `ON DELETE CASCADE`;
  `to_chapter` NOT NULL; `to_verse_start` NOT NULL; `to_verse_end` NULL. Index
  `(to_book_id, to_chapter, to_verse_start)` for read-time target lookup. **No
  `from_verse_id`** — the source verse is derived from `footnote.verse_id` (the private
  repo's `from_verse_id` is redundant here).
- The loader resolves each cross-ref's `to_book_order_index` to *this translation's*
  `books.id` after all books are inserted, then inserts `cross_references` rows. The
  explicit delete-cascade walk is extended to remove `cross_references` before `footnotes`.

## Options considered

- **A — Enrich the existing footnote model (additive).** *Chosen.* One note concept, one
  table; the bundled footnotes simply *are* untyped notes.
- **B — Separate `notes` concept alongside `footnotes`.** Rejected: two near-identical
  concepts for the same thing, duplicate loader/read paths, and the reader UI would have to
  merge two streams.
- **C — Generic JSON `metadata` blob on footnotes.** Rejected: defeats Pydantic/SQLAlchemy
  validation (CLAUDE.md: "no raw dicts in or out"), unqueryable, pushes structure into
  application code.

## Consequences

- **Positive:** one note model end-to-end; bundled translations untouched (NULL columns);
  NET's full note richness is representable; cross-refs are range-capable and tolerant of
  imperfect (regex-based) extraction; FTS over verses/notes can be layered on later without
  schema churn.
- **Costs:** `footnotes` gains sparse NULL columns for the 13 bundled translations
  (cheap in SQLite). Cross-ref targets are stored unresolved (book + chapter + verse
  numbers), so the reader resolves them at query time. The `note_type` vocabulary is a
  coupling point — it bakes NET's four types into a translation-agnostic schema; adding a
  value later is additive and non-breaking.
- **Non-goals (separate future slices):** FTS over verses/notes; reader UI rendering of
  notes/cross-refs; re-parsing or migrating the 13 bundled translations.

## Implementation cycles

1. **Canonical schema only** — `CanonicalCrossRef` + optional enrichments on
   `CanonicalFootnote` + validators. Verified by schema tests (backward-compat, round-trip,
   rejections).
2. **DB model + migration + loader** — nullable `footnotes` columns, `cross_references`
   table + model, one Alembic migration (reversible), loader inserts + resolves cross-refs.
   Verified with a hand-built mini fixture.
3. **Port the NET parser + canonical adapter** — `parsers/net.py` (interface preserved)
   plus an adapter mapping `body→text`, `type→note_type`, `word_offset→char_offset`,
   `to_book_short→to_book_order_index` (NET-abbreviation→canonical map). Verified by adapter
   unit tests.
4. **Real ingest + count validation** — run on `bibles/net.pdf`, load, compare verse/note/
   cross-ref counts against the private repo's known totals.
