# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Verse highlights / annotations.** Select verse text to highlight it in one of
  six colors; highlights can span multiple verses, overlap (shown with a `+N`
  badge), and carry an optional plain-text note. Edit color/note or delete from an
  annotation panel — a docked side-panel on desktop, a slide-up bottom-sheet on
  mobile — with touch text-selection supported. A highlight is visible only in the
  translation it was made in. Backed by a user-scoped annotations CRUD API
  (anchored by canonical coordinates + translation code, not verse/translation
  foreign keys, so a translation reload can't orphan highlights).
- **Scripture full-text search.** A "Search Scripture" surface searches verse text
  and translator's notes via SQLite FTS5 — one translation, or all loaded
  translations grouped to one row per canonical verse — kept distinct from the
  existing journal-entry keyword search.
- **NET Bible support with translator's notes and cross-references.** A NET parser
  (`python -m soap_journal.parsers.net`), an enriched canonical schema + data model
  carrying typed notes (`tn/sn/tc/map`, character-anchored, with cross-references)
  and a `cross_references` table, a read API that returns them inline per verse, and
  a reader that renders inline note markers + tappable cross-reference navigation.
  NET text is user-supplied (not bundled); see `bibles/README.md`.
- Reader resilience: an unknown or stale translation code in the URL now falls back
  to a loaded translation instead of a dead "unable to load" screen.
- `build-translation` CLI subcommand
  (`python -m soap_journal.cli build-translation --code ESV <source> [--out <path>]`)
  that parses a Bible source file and validates the result against the canonical
  schema in one step, writing the output only if validation passes. Collapses the
  former parse-then-validate flow into a single command for any of the 17
  supported translation codes; touches no database.
- `validate-translation` CLI subcommand
  (`python -m soap_journal.cli validate-translation <path.json>`) that checks a
  parser's canonical JSON against the schema and reports book/chapter/verse
  counts without touching the database — for vetting a translation off-device
  and as the reference implementation for a future TypeScript validator.

- NKJV parser (`python -m soap_journal.parsers.nkjv`) for users who have
  their own New King James Version PDF.
- KJV parser (`python -m soap_journal.parsers.kjv`) with section heading
  extraction — the first parser to populate the reader's heading display.
- KJV (King James Version) bundled as a second out-of-box translation
  alongside BSB. The side-by-side comparison view is now active on every
  fresh install.
- Docker entrypoint bootstraps each bundled translation independently
  (idempotent per-translation, not all-or-nothing).
- `bibles/` directory for user-provided copyrighted Bible source files
  (gitignored; `bibles/README.md` explains usage).
- ESV parser (`python -m soap_journal.parsers.esv`) for users who have
  their own English Standard Version PDF. First parser to extract
  footnotes into the canonical schema.
- NLT parser (`python -m soap_journal.parsers.nlt`) for users who have
  their own New Living Translation PDF. First parser to use `pdftotext`
  (poppler-utils) for two-column PDF extraction.
- 11 new book abbreviation aliases (Deu, Rut, Sol, Joe, Amo, Oba, Mat,
  Mar, Joh, Phi, Jam) to support NKJV and common shorthand.
- 17 new ordinal book-name aliases (1st Samuel, 2nd Kings, 3rd John,
  etc.) to support NLT.
- Eleven additional public-domain translations bundled by default
  (AKJV, ASV, CPDV, DBT, DRB, ERV, JPS, SLT, WBT, WEB, YLT).
  Refactored KJV parser into a shared PDFMaker-format module so all
  twelve PDFMaker translations share one codebase.
- Docker entrypoint now bootstraps all 13 bundled translations with
  per-translation progress logging and failure isolation.
- `poppler-utils` added to the runtime image and `./bibles` bind-mounted
  read-only at `/app/bibles`, so user-provided copyrighted PDFs (ESV,
  NLT, NKJV) can be parsed and loaded entirely inside the container.
  `bibles/README.md` rewritten with step-by-step Docker instructions.

### Fixed

- NLT parser now handles both `pdftotext` builds (Xpdf inline verse
  markers and poppler standalone markers), so it works in-container.

## [0.1.0] — 2026-05-27

Initial release.

### Added

- SOAP journaling with auto-pulled Scripture text from a configurable
  translation.
- Bible reader with the Berean Standard Bible (BSB) bundled.
  Verse-by-verse and paragraph layouts, adjustable font size, jump bar
  that accepts both full and abbreviated book names.
- Multi-user accounts. First registered user becomes admin;
  open-registration can be toggled at runtime by the admin.
- Long-lived cookie sessions with an explicit Log Out button. Password
  hashing via argon2.
- Admin panel for user management (create, delete, reset password,
  promote / demote, view loaded translations).
- Entry list with keyword search, book / tag / date-range filtering,
  and pagination.
- Calendar view of entries by month.
- "On this day in previous years" surfacing on the dashboard.
- Cross-reference badge in the reader linking a chapter back to the
  user's own entries on it.
- Light and dark themes, persisted across browser restarts.
- Docker Compose deployment. BSB is bootstrapped automatically on the
  container's first start.
- Parser architecture (`soap_journal.parsers`) for adding new
  translations via a small CLI.
- Top-level error boundary so render-time errors never produce a blank
  page.

### Known limitations

- Only the BSB ships in the repo. Other translations require writing a
  parser and loading the resulting canonical JSON with the
  `load-translation` CLI.
- Side-by-side translation comparison is shown as a disabled
  affordance in the reader until a second translation is loaded.
- No self-service password reset; the admin resets passwords from the
  admin panel.
- HTTPS is not built-in. Put a reverse proxy in front of the container
  if you want TLS.
- No outbound internet calls at runtime by design — that means no
  telemetry, no auto-updates, and no email features.

[0.1.0]: https://github.com/kbennett2000/soap-journal/releases/tag/v0.1.0
