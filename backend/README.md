# backend

soap-journal FastAPI backend. See the repo root `README.md` and `CLAUDE.md`
for project overview, conventions, and engineering principles.

## Dependencies

- `requirements.txt` — runtime dependencies only. This is what production
  Docker images install.
- `requirements-dev.txt` — runtime plus test/lint tooling. Install this in
  your local dev venv.

```bash
pip install -r requirements-dev.txt
```

## Tests

Tests live next to the code as `*_test.py` siblings (see `CLAUDE.md`).
Run them from this directory:

```bash
pytest -v
```

The default suite includes two tests that exercise the bundled BSB source
(parser + canonical-schema smoke). On a modern machine the full suite still
runs in well under 10 seconds. If the BSB source is missing from
`bible-sources/bsb/bsb.txt` those two tests skip automatically.

## CLI tools

`python -m soap_journal.parsers.bsb <source.txt> --out <canonical.json>`
parses the official BSB tab-separated plain text into the canonical JSON
schema. The CLI uses Python's `argparse` (no extra dep) — simple enough
that adding `typer` for one command isn't worth it. Add a new parser by
dropping a sibling module under `soap_journal/parsers/` that emits the
same canonical format.

`python -m soap_journal.cli load-translation <canonical.json>` loads a
canonical JSON file into the configured database (reads `DATA_DIR` from
the env-resolved `Settings`). Re-running with the same `code` replaces
the existing translation atomically; the loader is idempotent.

## SECRET_KEY

The `SECRET_KEY` env var signs session cookies. It is resolved at app startup
in this order:

1. If `SECRET_KEY` is non-empty in the environment (or `.env`), use it as-is.
2. Otherwise, if `{DATA_DIR}/.secret_key` exists, read and use that.
3. Otherwise, generate a 64-byte URL-safe token, write it to
   `{DATA_DIR}/.secret_key` with mode `0600`, and use that.

The user's `.env` is never modified. To rotate the key, delete the
`.secret_key` file (and/or set `SECRET_KEY=` in your environment) and restart.
