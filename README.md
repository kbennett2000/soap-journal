# soap-journal

![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![React 18](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)

A self-hosted, offline-first SOAP (Scripture, Observation, Application, Prayer) journaling app with an integrated Bible reader. It runs on **Windows, Mac, or Linux** with Docker — perfect on a dedicated home server over your LAN, and just as happy on the computer you use every day. No internet required after install.

**Status:** in development. Not yet released.

> **New here?** The [install guide](docs/install/README.md) has a friendly, step-by-step walkthrough for **Windows**, **Mac**, and **Ubuntu/Linux servers** — Docker setup, configuration, first login — with screenshots. The Quick Start below assumes you're comfortable with Docker already.

![Dashboard showing recent entries and the "On this day in previous years" panel](docs/screenshots/usage-dashboard-populated.png)

![Bible reader showing John chapter 3 with the controls bar and "1 entry on this chapter" badge](docs/screenshots/usage-reader-john-3.png)

![New entry form pre-filled from clicking John 3:16 in the reader, with the Scripture preview rendered](docs/screenshots/usage-entry-form-from-verse.png)

![Entry detail page showing the snapshotted verse text, Observation, Application, Prayer, and tags](docs/screenshots/usage-entry-detail.png)

## Features

- SOAP-method journaling with auto-pulled Scripture text
- Built-in Bible reader — 13 public-domain translations bundled, side-by-side compare, jump bar, verse/paragraph layouts
- Optional **NET Bible** with inline translator's notes (translator/study/text-critical/map) and tappable cross-reference navigation
- **Verse highlights** in six colors — span multiple verses, overlap, carry an optional note; edit or delete from a panel (desktop) or bottom-sheet (mobile); a highlight shows only in the translation it was made in
- **Scripture full-text search** over verse text and translator's notes (one translation or all of them) — separate from journal-entry search
- Multi-user with simple username/password auth — admin can manage accounts
- Search, tag, filter, and calendar view of your entries
- "On this day in previous years" surfacing
- Cross-reference from any passage back to entries you've written on it
- Responsive UI for mobile and desktop, including touch text-selection for highlighting
- Light and dark themes
- 100% offline once installed — no telemetry, no external API calls

## Requirements

- **Windows, Mac, or Linux** with [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac) or Docker Engine + Compose (Linux)
- ~1 GB disk on Linux for the app and bundled Bible text; ~4 GB on Windows/Mac (Docker Desktop itself is larger)

## Quick Start

```bash
git clone https://github.com/kbennett2000/soap-journal.git
cd soap-journal
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
docker compose up -d
```

On the machine running it, open `http://localhost:8045`. From other devices on your LAN, use that machine's IP, e.g. `http://192.168.1.50:8045`. The first user to register becomes the admin.

**What you get out of the box:** on first start, the server loads 13 public-domain Bible translations automatically: BSB, KJV, AKJV, ASV, CPDV, DBT, DRB, ERV, JPS, SLT, WBT, WEB, and YLT. The side-by-side translation comparison view is active from the start. First boot takes several minutes while translations are parsed and loaded; subsequent restarts are fast.

For a step-by-step walkthrough — installing Docker, configuration, first login — pick your platform in the [install guide](docs/install/README.md) ([Windows](docs/install/windows.md), [Mac](docs/install/macos.md), [Ubuntu/Linux server](docs/install/ubuntu-server.md)). For everything else (the reader, journaling, tags, search, calendar, admin tasks, backups) see the [usage guide](docs/usage/README.md).

## Configuration

All configuration lives in `.env`:

| Variable     | Default     | Description                                       |
| ------------ | ----------- | ------------------------------------------------- |
| `PORT`       | `8045`      | Host-side port published by Compose               |
| `SECRET_KEY` | (generated) | Session signing key; auto-generated on first run  |
| `DATA_DIR`   | `/data`     | (Advanced) data path inside the container         |
| `BIND_HOST`  | `0.0.0.0`   | (Advanced) address the server binds to inside the container |

Self-registration is controlled at runtime by the admin through the API
(`PUT /api/v1/admin/settings`). On a fresh install it defaults to off; the
first user to register becomes the admin and can flip it on for everyone else.

## Updating

```bash
git pull
docker compose up -d --build
```

Migrations run automatically on the next start.

## Backups

Everything you care about lives in `./data` on the host. Stop the container, copy the folder, restart. Restore by copying it back.

## Troubleshooting

The most common issues are covered in [`docs/install/troubleshooting.md`](docs/install/troubleshooting.md). The greatest hits:

- **Port already in use** — change `PORT` in `.env` (e.g. `PORT=9090`) and `docker compose up -d`. The container always binds 8080 internally; Compose maps that to whatever host port you choose.
- **Permission errors on `./data`** (Linux only) — the container runs as UID 1000. If your host UID differs and you've bind-mounted an existing `./data`, run `sudo chown -R 1000:1000 ./data` once. On Docker Desktop (Windows/Mac) this doesn't apply — the file sharing layer handles ownership.
- **Viewing logs** — `docker compose logs -f` (or `docker compose logs --tail=100 soap-journal`).
- **Forgot the admin password** — see [Forgot the admin password](docs/install/troubleshooting.md#i-forgot-the-admin-password).
- **Want HTTPS?** v1 ships HTTP only on the assumption you're on a trusted LAN. Run a reverse proxy (Caddy, nginx, Traefik) in front of the container yourself — first-class HTTPS is a v2 topic.

## Bundled Bibles

This software bundles 13 public-domain translations out of the box:

| Code | Translation | License |
|------|------------|---------|
| BSB | Berean Standard Bible | Permissive |
| KJV | King James Version | Public domain |
| AKJV | American King James Version | Public domain |
| ASV | American Standard Version (1901) | Public domain |
| CPDV | Catholic Public Domain Version | Public domain |
| DBT | Darby Bible Translation (1890) | Public domain |
| DRB | Douay-Rheims Bible | Public domain |
| ERV | English Revised Version (1885) | Public domain |
| JPS | JPS Tanakh / Weymouth NT | Public domain |
| SLT | Smith's Literal Translation (1876) | Public domain |
| WBT | Webster's Bible Translation (1833) | Public domain |
| WEB | World English Bible | Public domain |
| YLT | Young's Literal Translation (1898) | Public domain |

All are parsed and loaded into your database automatically on the
container's first boot. Each translation is checked independently — if one
is already loaded, only the missing ones are parsed.

## Adding a Bible Translation

Beyond the 13 bundled translations, parsers are included for four
user-supplied translations you can add if you have your own copy of the
source: three copyrighted — **NKJV**, **ESV**, **NLT** — and the **NET**
(New English Translation). The repo ships none of this text.

**NET is special:** it carries the NET's extensive **translator's notes**
(typed translator/study/text-critical/map) and **cross-references**, which
the reader renders inline and which scripture search can search. Loading
NET is what lights up the notes/cross-reference features. Its full
build/load walkthrough (a large two-column PDF) is in
[`bibles/README.md`](bibles/README.md).

Drop the PDF into the gitignored `bibles/` directory, then build and load
it inside the running container. `./bibles` is bind-mounted to
`/app/bibles`, so for example:

```bash
docker compose exec soap-journal \
  python -m soap_journal.cli build-translation --code ESV /app/bibles/esv.pdf --out /tmp/esv.json
docker compose exec soap-journal \
  python -m soap_journal.cli load-translation /tmp/esv.json
```

`build-translation` is the one-step path: it runs the matching parser and
validates the result against the canonical schema in a single command,
writing the output file only if validation passes (so a failed build never
leaves a half-baked JSON behind). It reports the book/chapter/verse counts and
touches no database — ideal for turning your own PDF into an import-ready file
to load or to transfer to another device. `--out` defaults to
`./<lowercase-code>.json` if omitted.

If you'd rather run the steps separately, the parser
(`python -m soap_journal.parsers.esv <pdf> --out <path>`) and
`validate-translation <path.json>` are still available; `build-translation`
simply composes the two.

Step-by-step instructions for each of NKJV, ESV, NLT, and NET — including
the source format each expects and per-translation caveats — are in
[`bibles/README.md`](bibles/README.md). The side-by-side comparison view
is active out of the box (13 translations ship by default).

**Note on copyright:** only translations you have the legal right to use
should be loaded onto your instance. The 13 bundled translations are
public domain or permissively licensed; many modern translations (ESV,
NIV, NASB, etc.) are not. Loading a copyrighted translation onto a server
you control for personal use is between you and the publisher.

## Manual install without Docker (Linux / macOS)

Docker is the recommended path. If you can't or won't run Docker, you can
install the pieces directly. The commands below are for Linux and macOS;
Windows users without Docker should follow the
[advanced Windows guide](docs/install/windows-manual.md) (PowerShell
equivalents).

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head

# Load the bundled translations. The Docker path loads all 13 automatically;
# here you parse + load each one yourself. BSB first (tab-separated text):
python -m soap_journal.parsers.bsb ../bible-sources/bsb/bsb.txt --out /tmp/bsb.json
python -m soap_journal.cli load-translation /tmp/bsb.json
# ...then the 12 PDFMaker translations (or any subset you want):
for code in kjv akjv asv cpdv dbt drb erv jps slt wbt web ylt; do
    python -m soap_journal.parsers."$code" "../bible-sources/$code/$code.pdf" --out "/tmp/$code.json"
    python -m soap_journal.cli load-translation "/tmp/$code.json"
done

# Frontend
cd ../frontend
npm ci
npm run build

# Run (backend serves the built frontend).
# Change --port to serve on a different port (the Docker path uses PORT in .env).
cd ../backend
FRONTEND_DIST_DIR=../frontend/dist DATA_DIR=./data \
    uvicorn soap_journal.main:create_app --factory --host 0.0.0.0 --port 8045
```

## Development

See `SPEC.md` for the full specification, `CLAUDE.md` for engineering
conventions, and [`docs/adr/`](docs/adr/README.md) for the design history
(the architecture decision records, indexed).

```bash
# Backend (auto-reload, no static frontend mount in this mode)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn soap_journal.main:create_app --factory --reload --port 8045

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Tests: `cd backend && pytest` runs the fast suite (real full-PDF parses are
marked `slow` and excluded by default; run everything with
`pytest -m "slow or not slow"`), and `cd frontend && npm run test` runs the
Vitest suite. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full loop.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for development setup, branch
conventions, and the project's philosophy on scope.

## Changelog

Release notes live in [`CHANGELOG.md`](CHANGELOG.md).

## License

MIT — see [`LICENSE`](LICENSE). Third-party software notices live in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
