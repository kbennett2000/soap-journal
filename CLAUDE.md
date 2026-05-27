# CLAUDE.md

## Project Overview

`soap-journal` is a self-hosted, offline-first SOAP (Scripture, Observation, Application, Prayer) journaling app with an integrated Bible reader. It runs on an Ubuntu server over a local LAN with zero internet dependency after install, serves multiple users from a single instance, and is distributed under MIT for anyone to clone and run.

## Tech Stack

**Backend**
- Python 3.12
- FastAPI (latest stable)
- SQLAlchemy 2.x (async)
- Alembic (migrations)
- SQLite (single-file DB)
- Pydantic v2 (validation)
- Passlib + argon2 (password hashing)
- uvicorn (ASGI server)

**Frontend**
- React 18
- TypeScript (strict mode)
- Vite (build tool, dev server)
- Tailwind CSS
- React Router
- TanStack Query (server state)
- Zod (runtime validation, share schemas with backend where useful)

**Deployment**
- Docker + Docker Compose
- Single container OR backend + frontend-build served by backend (preferred: backend serves built frontend static files)

## Architecture

- **Monorepo** with `/backend` and `/frontend` at the root.
- Backend serves the built frontend as static files in production; in dev, Vite runs separately and proxies `/api` to FastAPI.
- All API routes live under `/api/v1/...`. No versioning gymnastics yet; v1 is the only version.
- Backend layout:
  - `backend/soap_journal/api/` — route handlers, grouped by resource (`entries.py`, `bible.py`, `auth.py`, `users.py`, `tags.py`, `admin.py`).
  - `backend/soap_journal/core/` — business logic, independent of FastAPI (services, domain functions).
  - `backend/soap_journal/db/` — SQLAlchemy models, session, Alembic env.
  - `backend/soap_journal/parsers/` — Bible parsers. Each parser is a CLI module: `python -m soap_journal.parsers.<name> <input> --out <path>`. Parsers output the canonical Bible JSON format and never touch the running DB; loading into the DB is a separate `load_translation` command.
  - `backend/soap_journal/schemas/` — Pydantic request/response models.
  - `backend/soap_journal/config.py` — env-driven settings (Pydantic Settings).
  - `backend/soap_journal/main.py` — FastAPI app factory + static mount.
- Frontend layout:
  - `frontend/src/components/` — reusable UI components (PascalCase files).
  - `frontend/src/routes/` — route-level page components.
  - `frontend/src/lib/` — API client, utilities, helpers.
  - `frontend/src/hooks/` — custom hooks.
  - `frontend/src/types/` — shared TS types.
- **Canonical Bible format**: parsers output to a normalized JSON schema (book, chapter, verse, text, plus optional metadata for headings/footnotes/red-letter). The app only ever reads this canonical format. A new translation = new parser + load step. The schema is defined in `backend/soap_journal/parsers/schema.py` and must not be changed casually.
- **Data directory**: a single configurable folder (default `./data/`) holds the SQLite DB, loaded Bible JSON, and any future uploads. Mount as a Docker volume.
- **Config via `.env`**: `PORT`, `DATA_DIR`, `SECRET_KEY`, `OPEN_REGISTRATION` (admin can flip at runtime too).

## Conventions

- **Python**: `snake_case` for everything except classes (`PascalCase`). Type hints everywhere. Prefer `async def` for I/O. No bare `except`. Use `pathlib.Path`, not `os.path`.
- **TypeScript**: `camelCase` for variables/functions, `PascalCase` for components, types, and interfaces. No `any` — use `unknown` and narrow. Strict mode on.
- **Imports**: absolute imports in both Python (`from soap_journal.x import y`) and TypeScript (configure `@/` alias for `src/`). No relative `../../` chains beyond one level.
- **Files**: one React component per file, file named after the component. Python modules lowercase. Tests live next to the code in `_test.py` / `.test.ts` siblings.
- **API contracts**: every endpoint has Pydantic request and response models. No raw dicts in or out.
- **Errors**: backend uses FastAPI's `HTTPException` with a small set of structured error codes; frontend has a single error boundary and a typed `ApiError` class.
- **Migrations**: every schema change ships with an Alembic migration. No `create_all` in production paths.
- **Secrets**: never committed. `SECRET_KEY` is generated on first run if absent and written to `.env`.
- **Verse references**: parsed centrally in `core/references.py`. Accept full and abbreviated book names. Both `John 3:16` and `Jn 3:16` and `Rom 8:28-30` must work.
- **Styling**: Tailwind utility classes inline; extract to a component when a pattern repeats 3+ times. Dark mode via Tailwind's `dark:` variant, toggled by a class on `<html>`.
- **No client-side routing tricks**: SPA with React Router, backend serves `index.html` for unknown non-`/api` routes.

## Out of Scope for v1

Do not build any of these unless explicitly asked. They are deliberately deferred:

- Reading plans (chronological, M'Cheyne, Bible-in-a-year, etc.)
- Bookmarks and highlights in the reader
- Export to Markdown / PDF / zip
- Built-in backup tooling (users copy the data folder)
- "Random entry" / rediscover surfacing
- Self-service password reset, security questions, email anything
- User-to-user sharing of entries
- Mobile apps (the responsive web UI is the mobile experience)
- Real-time sync / multi-device conflict handling beyond standard last-write-wins
- Any feature requiring an outbound internet call at runtime
- Non-BSB translations shipping in the repo (parser architecture must support them; only BSB loads in v1)
- Audio Bible, commentary integration, original-language tools
- Admin analytics dashboards beyond user management

## Git Workflow

After any code change is complete and verified (tests pass / lint clean /
feature works), do the following without being asked:

1. `git add -A` to stage all changes
2. Commit with a concise conventional-commit message
   (e.g. `feat: add user auth middleware`, `fix: handle empty cart edge case`,
   `refactor: extract validation into shared module`, `docs: update README`)
3. `git push` to push to origin/main

Commit at logical checkpoints — a complete feature, a bug fix, a refactor —
not after every individual file edit. If a task spans multiple commits,
make each commit independently meaningful and atomic.

If `git push` fails (auth, conflict, network), surface the full error to the
user immediately. Do not retry silently or attempt destructive resolutions
(no `--force`, no resetting branches).

Never commit secrets, API keys, .env files, or anything matching .gitignore.

## Engineering Principles

### Tests are required, not optional
- Every new feature, bug fix, or non-trivial change ships with tests.
- For new functionality, prefer test-first: write the test from the spec,
  then implement until it passes.
- A task is not "done" until the relevant tests pass. Do not report completion
  with failing or skipped tests.
- When fixing a bug, first write a test that reproduces the bug (and fails),
  then fix it. This prevents regressions.
- Keep the test suite fast. If a test is slow, isolate it (mark as integration
  or e2e) so the default `test` command stays under 10 seconds for unit tests.

### Tight feedback loops
- Use strict typing everywhere (TypeScript strict mode / Pydantic / Zod —
  whatever the stack supports). Type errors should surface immediately.
- Run lint and typecheck before declaring a task complete.
- Add structured logging at module boundaries from day one. When something
  breaks, logs should narrow the cause in seconds, not minutes.
- If a change requires manual verification (UI, integrations), state exactly
  what to check and how — don't leave it implicit.

### Spec before code for non-trivial work
- For any task touching 3+ files, introducing a new module, or changing a
  contract between components: produce a spec FIRST in plan mode. Do not
  start editing until the user has approved the plan.
- For significant architectural decisions, write a short ADR (Architecture
  Decision Record) in `/docs/adr/` capturing: context, options considered,
  decision, consequences. Reference the ADR in commit messages.
- Read `/docs/` and `/specs/` (if they exist) before starting work. Those
  files describe intent; the code describes implementation. Both matter.

### Taste and restraint
- Prefer the simplest solution that solves the problem. Resist adding
  abstraction, config options, or framework features that aren't justified
  by an actual requirement.
- If a diff is getting large, stop and ask whether the task should be
  decomposed into smaller commits.
- Reuse existing patterns in the codebase before inventing new ones.