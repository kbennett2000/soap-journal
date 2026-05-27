# Contributing to soap-journal

Thanks for the interest! soap-journal is a small, personal-server app.
Contributions that keep it that way — focused, easy to host, minimal
moving parts — are welcome.

## Philosophy

soap-journal is **a personal-server app, not a SaaS**. Decisions favor:

- One binary container, one config file, one data folder.
- Zero outbound internet calls at runtime.
- Plain HTML/CSS/JS in the browser, no exotic frameworks.
- A schema you can read on one screen.

If a change adds a moving part (a queue, a cache layer, a third-party
service, a build-time secret), it probably belongs in a different
project. See `SPEC.md` § "Out of Scope for v1" and `CLAUDE.md`
§ "Engineering Principles".

## Development setup

Pick the half you want to work on:

- Backend: see [backend/README.md](backend/README.md).
- Frontend: see [frontend/README.md](frontend/README.md).
- End-to-end (Docker): see the repo-root `README.md` "Quick Start".

## Running tests

- Backend: `cd backend && pytest`
- Frontend: `cd frontend && npm run test`
- Lint and typecheck the frontend: `npm run lint && npm run typecheck`
- Lint the backend: `cd backend && ruff check soap_journal && ruff format --check soap_journal`

Tests must pass before opening a PR. New features ship with tests; bug
fixes ship with a regression test.

## Branches and commits

- Branch off `main`. Use a prefix that matches the change:
  - `feat/<short-slug>` — a new feature
  - `fix/<short-slug>` — a bug fix
  - `refactor/<short-slug>` — a refactor with no behavior change
  - `chore/<short-slug>` — tooling, docs, dependencies, etc.
- Conventional-commit-style commit messages (`feat:`, `fix:`,
  `refactor:`, `docs:`, `chore:`, `test:`).
- Squash on merge is fine. Each PR should be one cohesive change.

## Pull requests

- One PR per logical change. If you find yourself writing "and also …"
  in the description, split it.
- Reference the relevant `SPEC.md` section if you're adding or
  changing user-visible behavior.
- Include a short test plan: what you ran, what you saw.

## Issues

Open issues at <https://github.com/kbennett2000/soap-journal/issues>.
Helpful issues include:

- What you tried (specific URL, action, or command).
- What you expected.
- What you saw (error message, screenshot, log line).
- Your environment: OS, browser, Docker version if relevant.

If you're adding a feature, please open an issue first to discuss
scope. Features that pull the project away from the "personal-server
app" line above will likely be declined — better to find that out
before you write the code.

## License

By contributing, you agree your contributions are licensed under the
MIT license (see [`LICENSE`](LICENSE)).
