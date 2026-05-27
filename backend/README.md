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

## SECRET_KEY

The `SECRET_KEY` env var signs session cookies. It is resolved at app startup
in this order:

1. If `SECRET_KEY` is non-empty in the environment (or `.env`), use it as-is.
2. Otherwise, if `{DATA_DIR}/.secret_key` exists, read and use that.
3. Otherwise, generate a 64-byte URL-safe token, write it to
   `{DATA_DIR}/.secret_key` with mode `0600`, and use that.

The user's `.env` is never modified. To rotate the key, delete the
`.secret_key` file (and/or set `SECRET_KEY=` in your environment) and restart.
