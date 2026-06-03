# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_Nothing yet._

## [0.1.0] — 2026-06-03

First public release — a complete, offline-first SOAP journaling app with a
built-in Bible reader, runnable on Windows, Mac, or Linux.

### Added

**Journaling**

- SOAP journaling (Scripture, Observation, Application, Prayer) with the
  Scripture text auto-pulled from a configurable translation; free-form tags
  with autocomplete; an auto-generated title from the passage, or your own.
- Entry list with keyword search and book / tag / date-range filters, plus
  pagination; a month calendar view of your entries; "On this day in previous
  years" on the dashboard; and a cross-reference badge that links a chapter in
  the reader back to your own entries on it.

**Bible reader**

- 13 public-domain translations bundled and loaded automatically on first boot
  (BSB, KJV, AKJV, ASV, CPDV, DBT, DRB, ERV, JPS, SLT, WBT, WEB, YLT).
  Verse-by-verse and paragraph layouts, adjustable font size, a jump bar that
  accepts full and abbreviated book names, and side-by-side translation
  comparison — active out of the box.
- **Verse highlights** in six colors: span multiple verses, overlap (shown with
  a `+N` badge), and carry an optional note. Edit or delete from a docked panel
  (desktop) or a slide-up bottom-sheet (mobile), with touch text-selection. A
  highlight shows only in the translation it was made in, and is anchored by
  canonical coordinates so reloading a translation can't orphan it.
- **Scripture full-text search** over verse text and translator's notes via
  SQLite FTS5 — one translation, or all of them grouped to one row per verse —
  kept distinct from journal-entry search.
- **Optional NET Bible** (user-supplied) with typed translator's notes
  (`tn` / `sn` / `tc` / `map`, character-anchored) and cross-references rendered
  inline, with tappable cross-reference navigation.
- Reader resilience: an unknown or stale translation code in the URL falls back
  to a loaded translation instead of a dead "unable to load" screen.

**Accounts & admin**

- Multi-user accounts; the first registered user becomes admin, and open
  self-registration is toggled at runtime by the admin. Long-lived cookie
  sessions with an explicit Log Out button; password hashing via argon2.
- Admin panel for user management: create, delete, reset password,
  promote / demote, and view loaded translations.

**Adding your own translations (parsers & CLI)**

- A parser architecture (`soap_journal.parsers`) with parsers for user-supplied
  **NKJV**, **ESV**, **NLT**, and **NET** PDFs, plus the `build-translation` and
  `validate-translation` CLI subcommands that parse and validate against the
  canonical schema without touching the database. Includes broad book-name alias
  coverage (ordinals like "1st Samuel" and common shorthand). The gitignored
  `bibles/` directory is bind-mounted read-only at `/app/bibles`, and
  `pdftotext` (poppler-utils) ships in the image for two-column PDFs.

**Packaging & platforms**

- Docker Compose deployment; bundled translations are bootstrapped on first
  start with per-translation progress logging and failure isolation.
- Step-by-step install guides for **Windows, Mac, and Linux**, and a
  `.gitattributes` + Dockerfile line-ending safeguard so a Windows clone still
  boots the container cleanly.
- A top-level error boundary so a render-time error never produces a blank page.

### Fixed

- NLT parser now handles both `pdftotext` builds (Xpdf inline verse markers and
  poppler standalone markers), so it works in-container.

### Known limitations

- No self-service password reset; the admin resets passwords from the admin
  panel.
- HTTP only — put a reverse proxy in front of the container if you want TLS.
- No outbound internet calls at runtime by design: no telemetry, no
  auto-updates, no email features.

[Unreleased]: https://github.com/kbennett2000/soap-journal/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kbennett2000/soap-journal/releases/tag/v0.1.0
