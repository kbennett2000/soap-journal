# 0001. Consolidate PDFMaker-format Bible parsers into one shared module

Date: 2026-05-28
Status: Accepted

## Context

The project bundles Bible translations by converting source files into a
canonical JSON schema via per-translation parser CLIs
(`python -m soap_journal.parsers.<code>`). Eleven new public-domain
translations (AKJV, ASV, CPDV, DBT, DRB, ERV, JPS, SLT, WBT, WEB, YLT)
were obtained as PDFs produced by the **same** Acrobat PDFMaker pipeline
as the existing KJV PDF: identical inline verse layout, `BookName N`
chapter dividers, named section headings, Proverbs `Saying N` sub-headers,
and a per-translation `<CODE> [Online]` footer.

The KJV parser (`kjv.py`) already contained a complete, tested algorithm
for this exact format. The only things that vary between these twelve
translations are four metadata fields (code, name, language, copyright)
and the footer marker string. We needed a way to add eleven near-identical
parsers without eleven near-identical copies of a non-trivial state
machine.

## Decision

Extract the KJV algorithm into a shared module
`backend/soap_journal/parsers/pdfmaker_format.py`, parameterized by a
frozen `PdfMakerTranslationConfig` dataclass and a `make_cli_main(config)`
factory. A registry (`_pdfmaker_translations.py`) holds all twelve configs
as the single source of truth. Each translation keeps its own CLI module
(`kjv.py`, `asv.py`, …) as a ~10-line shim that pulls its config from the
registry — preserving the `python -m soap_journal.parsers.<code>`
entrypoint per translation. KJV's shim re-exports the original symbols so
its existing test suite passes unchanged (a byte-for-byte behavior
guarantee).

## Alternatives considered

- **Copy `kjv.py` eleven times, edit the constants.** Simple and obvious,
  but duplicates a ~250-line state machine twelve ways. Any bug fix or
  format tweak would need twelve edits, and the copies would inevitably
  drift. Rejected as an unmaintainable amount of duplication for code that
  is identical except for five values.
- **A plugin / dynamic-discovery system** (auto-register parsers by
  scanning a directory or entry points). More flexible, but the set of
  translations changes rarely and a plain dict registry is far easier to
  read, debug, and reason about. Rejected as over-engineering — the wrong
  complexity ceiling for the problem.

## Consequences

- Adding another PDFMaker-format translation is now ~3 steps: drop the PDF
  in `bible-sources/<code>/`, add one registry entry, write a NOTICE — no
  new algorithm code.
- A single place to fix format-handling bugs; all twelve translations
  benefit at once. (Conversely, a regression there affects all twelve —
  mitigated by the parameterized real-source test suite and KJV's
  unchanged tests.)
- The per-translation shim files still exist (one per CLI), so the module
  count didn't shrink — but each is trivial. This is a deliberate trade to
  keep the `-m soap_journal.parsers.<code>` entrypoint convention.
- Only applies to the PDFMaker format. BSB (plain text), NKJV, ESV, and
  NLT use different source formats and keep their own dedicated parsers;
  this module is not a general "all Bibles" parser.

## Revisit if

- A future translation claims to be PDFMaker-format but needs more than a
  config field to parse (e.g. a structurally different heading or verse
  scheme). At that point, either widen `PdfMakerTranslationConfig` with a
  narrowly-scoped option or give that translation its own parser rather
  than bending the shared one.
- The number of non-PDFMaker parsers grows enough that a second shared
  base (or a small parser framework) would remove real duplication across
  *those* formats too.
