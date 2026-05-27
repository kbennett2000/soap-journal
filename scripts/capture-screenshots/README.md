# Screenshot capture script

This is a developer-only tool. It drives a running `soap-journal` instance
with Playwright and writes PNGs to `../../docs/screenshots/`. End users do
not need to run it — the screenshots are committed to the repo.

Re-run it when the UI changes so the documentation stays in sync. It is
deterministic: the same seed data, the same screens, the same files,
overwritten in place.

## Prerequisites

- Node 20+ (`node --version`)
- A reachable `soap-journal` instance with an **empty database**.

Reset to an empty database with:

```bash
# from the repo root
docker compose down -v && docker compose up -d
# wait for healthy
docker compose ps
```

> ⚠️ `docker compose down -v` **deletes the SQLite DB** in the `data/`
> volume. Don't run this against an instance you care about.

## Install and run

```bash
cd scripts/capture-screenshots
npm install
npx playwright install chromium
BASE_URL=http://localhost:8080 npx tsx capture.ts
```

`BASE_URL` defaults to `http://localhost:8080`. Set it explicitly if your
instance binds a different port (e.g. `BASE_URL=http://localhost:8045`).

## What it does

1. Visits `/login` on a fresh instance → `install-login-page.png`.
2. Switches to the Register tab and fills in `alice` / `password123`
   (without submitting) → `install-register-tab.png`.
3. Submits the form. The first registered user becomes admin
   → `install-dashboard-first-time.png`.
4. Uses the live browser session (admin cookie) to create a second user
   `bob` and a dozen sample journal entries spanning a few weeks plus
   "on this day" entries from prior years.
5. Walks through every documented screen — reader, entry form, entries
   list, calendar, admin — and writes one PNG per screen.
6. Switches to a phone viewport (390×844, iPhone user agent) and captures
   four mobile shots.

Light theme everywhere; dark-theme variants are out of scope.

## Standalone seed

`seed.ts` is also runnable on its own if you just want a populated demo
instance and don't care about screenshots:

```bash
BASE_URL=http://localhost:8080 npx tsx seed.ts
```

It will register `alice` (admin, password `password123`), create `bob`
(non-admin, password `password123`), and write the same set of entries.
Same fresh-DB precondition applies.

## Troubleshooting

- **`Probe registered a user…`** or **`Instance already has users…`**:
  the target isn't fresh. Run `docker compose down -v && docker compose up -d`
  from the repo root, wait for `(healthy)`, and re-run.
- **`net::ERR_CONNECTION_REFUSED`**: the instance isn't reachable at
  `BASE_URL`. Check `docker compose ps` and adjust the URL.
- **Stale screenshots**: PNGs are overwritten on each run; if a file is
  missing, the script crashed before reaching that step — check the
  console output.
