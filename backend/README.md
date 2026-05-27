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
