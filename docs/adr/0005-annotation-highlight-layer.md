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

---

## Cycle 5b addendum — selectability redesign, selection→offset, single-verse create/remove

**Status:** Implemented (2026-06-02). Frontend, desktop-first, single-verse. Multi-verse,
overlap `+N` stacking, the mobile bottom-sheet / touch path, and full edit (color-change, note
body) remain 5c.

**Verse markup redesign.** ADR-0004 wrapped each verse in a `<button>` (click → new entry),
which blocked native text selection. 5b drops that button:

- The verse is a **selectable, non-interactive** element carrying `data-verse={n}` — a `<div>` in
  verse layout, an inline `<span>` in paragraph layout (`data-testid="verse-{n}"`).
- The **verse number is the new-entry control**: a focusable `<button
  data-testid="verse-{n}-new-entry" aria-label="New entry on {book} {ch}:{n}">` with a visible
  hover/focus affordance and an adequate hit target (it's the app's primary creation action — not
  an invisible superscript). Mobile tap-target sizing is deferred to 5c.
- Verse text renders as `<span data-text-segment>` runs. Note markers and the number control are
  **not** `data-text-segment`, so they are zero-width in the offset coordinate space — making it
  identical to the backend's `char_offset` and the stored annotation coordinates.

**Selection→offset seam.** `lib/selection.ts` splits a **pure core** from the live read:
`rangeToVerseSelection(range)` maps a `Range`-like object to `{verseStart, verseEnd, charStart,
charEnd, rect}` (summing only `[data-text-segment]` text, snapping marker/number points to the
nearest boundary, normalizing backward selections, returning `null` for collapsed/out-of-verse).
`resolveSelection()` is the only function touching `window.getSelection()` and just delegates to
the pure core.

**Testing strategy (the crux risk).** The pure core is unit-tested with **jsdom-constructed real
`Range`s** over a built verse DOM (marker-skip, multi-segment accumulation, boundary, backward
normalize, cross-verse, collapsed) — no `getSelection` mocking. Component tests inject the
resolver (`resolveSelectionFn` prop, default `resolveSelection`) to drive the popover with a
known selection. The live `resolveSelection()` delegator's real-drag behavior is manual/E2E only.

**Render.** `buildVerseParts(text, footnotes, highlights)` (was `buildVerseSegments`) adds
highlight edges as breakpoints and tags each text run with the covering highlights (a stack, so
5c overlap reuses the shape; 5b renders the single top one). Covered runs render as a
`data-text-segment` span with `background: var(--hl-{color})` and a `data-highlight-id`. The
six `--hl-<color>` CSS vars live in `index.css` with light values and class-based `.dark`
overrides. ChapterContent filters annotations to `translation_code === chapter.translation_code`
before rendering (inherited decision a, belt-and-suspenders over the per-translation list query).

**Create + Remove (single-verse).** A `mouseup` on the chapter resolves the selection: a
single-verse, non-collapsed selection opens a desktop popover of six color swatches → `POST
/annotations` with the resolved coords → the chapter's annotations query is invalidated and the
highlight re-renders. A **cross-verse selection is refused** (no popover) in 5b. Clicking an
existing highlight opens the same popover with a **Remove** action → `DELETE /annotations/{id}`
→ re-render (5b ships reversible highlights; color-change/full edit stay 5c). The popover stops
its own mouse events from re-triggering the chapter handler. Compare panes do not wire the
highlight layer in 5b (open item for 5c).

**Open for 5c (noted during 5b review):** create/delete mutations are fire-and-forget — a failed
`POST`/`DELETE` currently surfaces no user feedback (the popover has already dismissed); wire an
error toast / re-open on failure. The popover clamps its left edge only (right-edge overflow at
the viewport edge) and is a `role="dialog"` without a focus trap (Escape-to-dismiss is wired in
5b; full focus management is 5c). Compare panes don't wire the highlight layer.

---

## Cycle 5c-1 addendum — multi-verse highlight create

**Status:** Implemented (2026-06-02). Frontend, single-chapter multi-verse. Overlap `+N` stacking is
5c-2; the edit panel is 5c-3; touch is 5c-5.

5b refused cross-verse selections on create; 5c-1 handles them within one chapter. Most of the work
was already in place from 5b: `rangeToVerseSelection` already resolved a multi-verse range to
`(verse_start, char_start)..(verse_end, char_end)` — the start offset measured in `verse_start`'s
coordinate space and the **end offset in `verse_end`'s** (two independent `offsetWithinVerse` walks);
and `highlightSpansForVerse` + `buildVerseParts` already projected a multi-verse annotation onto each
verse (partial tail of `verse_start`, full middle verses, partial head of `verse_end`). 5c-1:

- **Removed the single-verse create gate** in `ChapterContent.handleMouseUp` — any non-null
  `VerseSelection` now opens the create popover; all four coordinates pass straight through to the 5a
  `POST` (the schema already carries `verse_start..verse_end`). Single-highlight Remove already works
  for a multi-verse highlight: every covered run carries `data-highlight-id={id}`, so clicking any of
  them removes the whole annotation with one `DELETE`.
- **Chapter-boundary guard** (`rangeToVerseSelection`): a selection whose ends resolve to different
  `[data-chapter]` elements is refused (the offsets would index different coordinate spaces). The
  reader renders one chapter (`<article data-chapter="{code}/{book}/{n}">`), so this can't happen in
  the single pane today; the guard is defensive and skipped when no `[data-chapter]` ancestor exists
  (bare unit-test DOM). Identity comparison of the two chapter elements, not the key string.

**Tested** (the coordinate math directly, per the 5b review's bug class): a 2→4-verse selection
resolves with the end offset in verse 4's space (a discriminating assertion — a bug measuring it in
verse 2's space would fall back to verse 2's length); a backward multi-verse selection normalizes; a
chapter-crossing selection is refused; render paints tail/full/head across the right verses
coexisting with a mid-verse marker and respects the translation filter; multi-verse create POSTs all
four coords (including the legitimate `char_end < char_start` cross-verse ordering); clicking any
covered span removes the whole multi-verse highlight. typecheck + lint + 195 tests green.
