# Session Handoff

_Last updated: 2026-05-28. Branch `feat/shared-pdfmaker-parser`, fully merged to `main` via PR #25 and PR #26. Working tree clean._

## Goal

Consolidate the Bible-parser codebase and expand bundled translations, then make user-provided copyrighted translations (ESV/NLT/NKJV) loadable inside the Docker container, refresh the docs, and improve repo discoverability.

## Done

- **Shared PDFMaker parser (PR #25).** Extracted the KJV algorithm into `backend/soap_journal/parsers/pdfmaker_format.py` (`PdfMakerTranslationConfig` dataclass + `make_cli_main` factory). `kjv.py` is now a thin shim re-exporting the same symbols so its tests pass unchanged. Registry at `backend/soap_journal/parsers/_pdfmaker_translations.py`; 11 new shim modules (`akjv, asv, cpdv, dbt, drb, erv, jps, slt, wbt, web, ylt`). 11 public-domain source PDFs + NOTICE files committed under `bible-sources/<code>/`.
- **Docker bootstrap.** `scripts/docker-entrypoint.sh` loads all 13 public-domain translations with `(N/13)` progress logging and per-translation failure isolation. `docker-compose.yml` healthcheck `start_period` → 600s.
- **In-container ESV/NLT/NKJV (PR #26).** Added `poppler-utils` to the Dockerfile; bind-mounted `./bibles` read-only at `/app/bibles`. Rewrote `bibles/README.md` with Docker-first parse+load steps. Refreshed stale docs (`docs/usage/03-reading-the-bible.md`, `docs/README.md`), root README, CHANGELOG.
- **NLT poppler fix.** `_preprocess` in `backend/soap_journal/parsers/nlt.py` now handles both Xpdf (inline markers) and poppler (standalone markers) output. +2 regression tests. All 91 ESV/NKJV/NLT parser tests pass.
- **Discoverability.** Repo description + 20 topics set via `gh repo edit`; static badge row added to README.

## Decisions

See `docs/adr/0001-shared-pdfmaker-parser.md` for the parser-consolidation decision. Other notable choices:

- **Docker-only instructions for user-provided translations**, with `poppler-utils` added to the image and `./bibles` bind-mounted — chosen over a host-parse workaround so all three (ESV/NLT/NKJV) load uniformly in-container.
- **NLT format normalization in `_preprocess`**: merge a standalone numeric line into the next line only when that line starts with a non-digit. This converts poppler's standalone verse markers to the inline form the parser expects, while leaving census counts (number-followed-by-number, e.g. Ezra 2) as continuation text. Works for both `pdftotext` builds.
- **Verse-gap placeholders**: omitted disputed verses (Acts 8:37, John 5:4, …) are filled with placeholder text so the canonical schema's 1..N invariant holds and verse numbers stay aligned across translations.

## In progress

None on the code side — all merged, working tree clean.

## Pending / next session

1. **User on-server deployment (live thread).** User is on `~/applications/soap-journal` (Ubuntu) loading ESV/NLT/NKJV. They must `git pull && docker compose up -d --build` to get `poppler-utils` + the `/app/bibles` mount, then parse with `docker compose exec soap-journal python -m soap_journal.parsers.<code> /app/bibles/<code>.pdf --out /tmp/<code>.json` and load. Confirm this succeeds.
2. **Social-preview image** — upload via GitHub web UI (Settings → General → Social preview), reusing a screenshot from `docs/screenshots/`. Highest-impact remaining discoverability item; cannot be done via CLI.

## Open questions

- **CI workflow?** No `.github/workflows` exists, so there's no automated test gate and no build badge. Worth adding (would make a build badge meaningful) — for the user to decide.

## Watch out for

- Container mount path is `/app/bibles`, NOT `/bibles`. The user hit this.
- `pdftotext` differs by implementation: the Docker image ships **poppler** (standalone verse markers); a typical Ubuntu/dev host may have **Xpdf** (inline markers). The NLT parser depends on the `_preprocess` normalization to handle both — don't "simplify" it away.
- "pdftotext not found" means the container is the pre-poppler image — a rebuild (`--build`) is required, not just `exec`.
- `bibles/*` is gitignored (copyrighted PDFs); only `bibles/README.md` is committed. `bible-sources/*` holds the committed public-domain PDFs.
