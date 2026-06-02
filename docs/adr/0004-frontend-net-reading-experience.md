# ADR 0004 — Frontend: surface the NET reading experience (notes, cross-refs, search)

**Status:** Accepted

**Date:** 2026-06-02

## Context

The backend now exposes, for the NET translation, typed translator's notes (`tn/sn/tc/map`
with `char_offset`/`marker`/`ordinal`), cross-references per note (ADR-0002), and FTS search
over verses + notes — single-translation and a grouped `translation=ALL` mode (ADR-0003). The
React frontend surfaces none of it: `types/api.ts`'s `FootnoteResponse`/`VerseResponse` are
stale (no rich-note fields), and there's no scripture-search UI. This is a **re-implementation**
of the NET app's reading UX in this repo's React 18 / Vite / TanStack Query / Tailwind patterns
— mining the SvelteKit app for interaction design and the offset-mapping algorithm only.

## Decisions

**1 — Translation-specific highlights are hidden outside their source translation.** A highlight
is `(char_start, char_end)` into ONE translation's verse text; those offsets are meaningless
against a differently-worded translation. An annotation will carry the translation it was made
in and render **only when the reader shows that translation**. Rejected: best-effort
cross-translation remap (fuzzy, fragile, wrong offsets — high cost, low value). *Schema note for
the deferred annotation layer:* the annotations table is **greenfield** (no rows to migrate) and
will anchor by **stable canonical coordinates + translation _code_** —
`(user_id, translation_code, book, chapter, verse_start, verse_end, char_start, char_end, color,
note)` — **not** a `verses.id`/`translations.id` FK: the loader replace-loads a translation
(delete+insert), so row ids change on reload and an FK would orphan highlights; canonical coords
+ code survive. The reader route already carries `translationCode`, so the render filter is
`annotation.translation_code === route code`.

**2 — Note rendering: inline markers from `char_offset`; plain translations unchanged.** Render
a verse's clean text with a superscript marker (numbered by `ordinal`) at each typed note's
`char_offset`; clicking opens a note view (type label + body + cross-ref links). A footnote with
`char_offset === null` (every plain translation; `note_type` null) renders exactly as today via
the existing end-of-verse `FootnoteMarker`. So BSB/KJV/etc. are visually unchanged; only NET
gains inline typed notes. The marker is a nested button that stops propagation so it doesn't
trigger the verse's existing new-entry click.

**3 — Cross-refs: render the structured list, not body regex.** The backend already extracts
`cross_refs` (`{to_book abbrev, to_chapter, to_verse_start, to_verse_end}`), so render them as
`<Link>`s into `/read/:translationCode/:book/:chapter` (book via the abbreviation alias the route
accepts) reusing ReaderPage's `?range=` highlight-on-arrival — no free-text linkifier.

**4 — Search UI distinct from entry search.** A dedicated scripture-search surface (route
`/read/search`, hook `useBibleSearch`, query key `["bible","search",...]`, labelled "Search
Scripture") with separate verse-hit and note-hit lists, sanitized `<mark>` snippets, reader
links, and a translation selector (current default + "All" → grouped). The existing entry
keyword search (`/entries?q=`) is untouched; the two are never merged.

**5 — Ship reader DISPLAY first; defer the annotation layer to ADR-0005.** This ADR covers
read-only display (notes, cross-refs, search UI) and needs **no backend changes**. The
highlight/annotation layer (selection→offset mapping, multi-verse overlay/segment-splitting,
selection popover, desktop side-panel / mobile bottom-sheet, plus a new annotations table + CRUD
API) is larger and independently valuable — it gets its own ADR-0005, planned separately, and
inherits Decision 1.

## Consequences

- Three small frontend cycles: (1) types + client + hooks + fixtures [this change]; (2) note +
  cross-ref rendering in the reader; (3) scripture search UI.
- The entry-form scripture preview stays a plain-text snapshot (notes are a reader concern).
- The annotation layer is explicitly out of scope here and large enough to re-plan before
  implementation.

## Cycle 1 (this change)

`types/api.ts` extended to match the backend exactly: `FootnoteResponse` gains
`note_type`/`char_offset`/`marker`/`ordinal`/`cross_refs`; new `CrossRefResponse`; search types
`SearchScope`/`VerseSearchHit`(incl. `translation_codes`)/`NoteSearchHit`/`SearchResponse`.
`lib/bible.ts` gains `searchBible`; `hooks/useBible.ts` gains `useBibleSearch`. MSW handlers +
`test/utils/bible.ts` builders extended (typed notes, cross_refs, `/bible/search`) as the
foundation for Cycles 2–3. No rendering or search UI yet.
