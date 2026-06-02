# ADR 0005 — Annotation / highlight layer

**Status:** Accepted

**Date:** 2026-06-02

## Context

ADR-0004 shipped the reader display (NET notes, cross-references, scripture search); the 13
plain translations are unchanged. This ADR adds user **highlights/annotations** on verse text —
the last major feature. It is a React re-implementation of the NET app's annotation layer
(mining its algorithms + interaction design, not transliterating Svelte) and spans the backend
(a greenfield `annotations` table + user-scoped CRUD) and the frontend (selectable verse markup,
DOM-selection→offset mapping, highlight rendering, a selection popover, and a desktop
side-panel / mobile bottom-sheet editor).

Two decisions are **inherited from ADR-0004** and not reopened: (a) a highlight is hidden
outside the translation it was made in; (b) annotations anchor by canonical coordinates +
`translation_code`, **not** a `verses.id`/`translations.id` foreign key.

**Implementation is phased.** Cycle 5a (this change) is the **backend only**: model, migration,
schemas, and user-scoped CRUD + tests. The frontend cycles (5b selectability redesign +
single-verse highlight; 5c multi-verse, overlap, mobile/touch) are each large and **re-planned
separately** before implementation.

## Decisions

**1 — FK-free anchor (decision b, the crux of the data model).** The `annotations` table stores
`(user_id, translation_code, book, chapter, verse_start, verse_end, char_start, char_end, color,
note)`. `translation_code` is a plain string and `book`/verse/char are plain integers — **no
foreign key to `verses` or `translations`.** The loader replace-loads a translation (delete +
insert in `cli/load_translation.py`), so `verses.id` and `translations.id` churn on every
reload; an FK would orphan or cascade-delete a user's highlights. Canonical coordinates + the
stable translation *code* survive reloads. Only `user_id` is a real FK (→ `users`, `ON DELETE
CASCADE`): a deleted user's annotations go with them.

**2 — Hidden outside source translation (decision a).** Each annotation carries the
`translation_code` it was made in; char offsets are only valid for that translation's text. The
reader renders an annotation only when its `translation_code` matches the chapter's translation
(frontend, 5b). The list endpoint filters by `translation_code` so a per-chapter fetch returns
only the right rows.

**3 — Color palette.** Six fixed colors — `yellow, green, blue, pink, orange, purple` — enforced
by a DB `CHECK` constraint (`ck_annotations_color`) and a Pydantic `Literal`, matching the NET
app's palette.

**4 — Per-chapter lookup index.** A compound index `(user_id, translation_code, book, chapter)`
serves the reader's "this user's highlights for this chapter" query without a separate sort.

**5 — User-scoped CRUD, modeled on Entry.** `api/annotations.py` + `core/annotations.py` mirror
the entries resource: every operation requires `get_current_user` and is scoped to `user_id`; a
cross-user access returns 404 (`ANNOTATION_NOT_FOUND`), never leaking another user's rows. PATCH
updates color and/or note (partial via `model_fields_set`). Kept entirely separate from entries.

**6 — Validation.** `verse_end >= verse_start`; for a single-verse annotation
(`verse_start == verse_end`), `char_end >= char_start`; offsets/chapters are non-negative/≥1;
`book` is normalized to its canonical name (`get_book_by_name`) and rejected if unknown; `color`
must be in the palette.

## Consequences

- A translation reload cannot orphan or cascade-delete highlights (FK-free anchor); the trade is
  that referential integrity to verses/translations is not DB-enforced — acceptable and
  intentional, since the canonical coordinate space is the contract.
- The backend lands and is reviewed before any UI, so the frontend builds against a real API.
- Frontend rendering, selection→offset mapping, multi-verse, overlap, and the responsive editor
  are **out of scope here** (5b/5c, separately planned). Note bodies are plain text for now
  (sanitized markdown is a later option; this repo has no marked/DOMPurify deps).
