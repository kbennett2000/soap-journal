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
pytest                        # fast unit suite — the default loop (slow tests excluded)
pytest -m "slow or not slow"  # everything, incl. the real-PDF integration tests
pytest -m slow                # only the slow real-PDF integration tests
```

Tests marked `slow` — the full-source parser integration tests that parse real
multi-thousand-page Bible PDFs (and the NET Genesis-1 smoke test) — are
**excluded from the default run** (via `addopts = -m "not slow"`) so it stays
fast. They still run explicitly and in CI (see `.github/workflows/`). A `slow`
test skips automatically when its source file isn't present (e.g. the
gitignored copyrighted PDFs).

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

## Reference syntax

The jump-bar endpoint `GET /api/v1/bible/resolve?ref=...` and the central
parser in `core/references.py` accept:

| Input                | Canonical          | Notes                              |
| -------------------- | ------------------ | ---------------------------------- |
| `John 3:16`          | `John 3:16`        | Single verse                       |
| `John 3:16-20`       | `John 3:16-20`     | Verse range within one chapter     |
| `John 3`             | `John 3`           | Whole chapter                      |
| `Jn 3:16`            | `John 3:16`        | Abbreviation                       |
| `1Cor 13`            | `1 Corinthians 13` | No-space numbered book             |
| `Song of Songs 2:1`  | `Song of Solomon 2:1` | Alias                           |
| `Apocalypse 22:21`   | `Revelation 22:21` | Alias                              |
| `john 3:16-20`       | `John 3:16-20`     | Case-insensitive                   |
| `John 3:16–20`       | `John 3:16-20`     | En dash or em dash also accepted   |

The parser is whitespace-tolerant and validates structure against the
static book list in `core/bible/books.py`; it does **not** verify the
chapter / verse range exists in any particular loaded translation (the API
layer does that and returns `REFERENCE_OUT_OF_RANGE` or `CHAPTER_NOT_FOUND`
when it does not).

### Not supported in v1

- **Cross-chapter ranges** (`John 3:30-4:2`). The parser rejects these
  with a dedicated `cross-chapter ranges are not supported` message. A v2
  syntax would need to decide how to render the second chapter's leading
  context; deferred until we have a UI need.
- **Multiple references in one call** (`John 3:16; Rom 8:28`). Rejected
  outright. The frontend should split on `;` / `,` itself and call
  `/resolve` once per reference if it needs both.

## Entry retrieval

`GET /api/v1/entries` accepts the filters `q`, `book`, `tag`, `from_date`,
`to_date`. All filters AND together; pagination (`limit`, `offset`) and
`order` work the same with or without them. `applied_filters` in the
response echoes what was applied so the frontend can render filter chips
without re-deriving from the URL — the echoed `book` is the canonical
name even if the user typed an alias.

### Why `LIKE` instead of FTS5

The `q` filter is `LIKE '%substring%'` (case-insensitive, %/_/\ escaped).
A single user's journal fits comfortably in a few thousand rows at any
realistic horizon, and SQLite scans them in milliseconds. FTS5 buys us
nothing measurable at v1 scale and would add a synced index to maintain
on every entry save. Revisit when search shows up slow.

### On this day — Feb 29

The query matches entries where `entry_date.month == target.month` AND
`entry_date.day == target.day`. So:

- Target = Feb 29 of a leap year → matches Feb 29 entries from prior
  leap years (24 % 4 == 0 etc.).
- Target = Feb 28 of a non-leap year → does **not** pull in Feb 29
  entries (day 28 ≠ day 29). This is intentional: the user asked for
  Feb 28, the system returns Feb 28s.

### Passage cross-references

`GET /api/v1/bible/passages/entries?ref=...` matches by **verse_id**.
Each translation has its own `verses` rows, so an entry created against
one translation will not be returned when querying another translation's
passage even if the (book, chapter, verse) numbering is identical.
Cross-translation matching by (book, chapter, verse) tuple is a v2
concern; deferred.

## SECRET_KEY

The `SECRET_KEY` env var signs session cookies. It is resolved at app startup
in this order:

1. If `SECRET_KEY` is non-empty in the environment (or `.env`), use it as-is.
2. Otherwise, if `{DATA_DIR}/.secret_key` exists, read and use that.
3. Otherwise, generate a 64-byte URL-safe token, write it to
   `{DATA_DIR}/.secret_key` with mode `0600`, and use that.

The user's `.env` is never modified. To rotate the key, delete the
`.secret_key` file (and/or set `SECRET_KEY=` in your environment) and restart.
