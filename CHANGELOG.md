# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
