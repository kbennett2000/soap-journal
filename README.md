# soap-journal

A self-hosted, offline-first SOAP (Scripture, Observation, Application, Prayer) journaling app with an integrated Bible reader. Designed to run on a home Ubuntu server over your local LAN — no internet required after install.

**Status:** in development. Not yet released.

> **New to self-hosting?** The [full install guide](docs/install/README.md) walks through every step on a fresh Ubuntu Server — Docker setup, configuration, first login — with screenshots. The Quick Start below assumes you've done this before.

![Dashboard showing recent entries and the "On this day in previous years" panel](docs/screenshots/usage-dashboard-populated.png)

![Bible reader showing John chapter 3 with the controls bar and "1 entry on this chapter" badge](docs/screenshots/usage-reader-john-3.png)

![New entry form pre-filled from clicking John 3:16 in the reader, with the Scripture preview rendered](docs/screenshots/usage-entry-form-from-verse.png)

![Entry detail page showing the snapshotted verse text, Observation, Application, Prayer, and tags](docs/screenshots/usage-entry-detail.png)

## Features

- SOAP-method journaling with auto-pulled Scripture text
- Built-in Bible reader (BSB and KJV bundled; more translations via a parser architecture)
- Multi-user with simple username/password auth — admin can manage accounts
- Search, tag, filter, and calendar view of your entries
- "On this day in previous years" surfacing
- Cross-reference from any passage back to entries you've written on it
- Responsive UI that works on mobile and desktop browsers
- Light and dark themes
- 100% offline once installed — no telemetry, no external API calls

## Requirements

- Ubuntu (or any Linux that runs Docker)
- Docker and Docker Compose
- ~1 GB disk for the app and bundled Bible text

## Quick Start

```bash
git clone https://github.com/kbennett2000/soap-journal.git
cd soap-journal
cp .env.example .env
docker compose up -d
```

Open `http://<your-server-ip>:8045` from any device on your LAN. The first user to register becomes the admin.

**What you get out of the box:** on first start, the server loads 13 public-domain Bible translations automatically: BSB, KJV, AKJV, ASV, CPDV, DBT, DRB, ERV, JPS, SLT, WBT, WEB, and YLT. The side-by-side translation comparison view is active from the start. First boot takes several minutes while translations are parsed and loaded; subsequent restarts are fast.

For a step-by-step walkthrough — installing Docker, finding your server's IP, first login — see the [install guide](docs/install/README.md). For everything else (the reader, journaling, tags, search, calendar, admin tasks, backups) see the [usage guide](docs/usage/README.md).

## Configuration

All configuration lives in `.env`:

| Variable     | Default     | Description                                       |
| ------------ | ----------- | ------------------------------------------------- |
| `PORT`       | `8045`      | Host-side port published by Compose               |
| `SECRET_KEY` | (generated) | Session signing key; auto-generated on first run  |
| `DATA_DIR`   | `/data`     | (Advanced) data path inside the container         |

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
- **Permission errors on `./data`** — the container runs as UID 1000. If your host UID differs and you've bind-mounted an existing `./data`, run `sudo chown -R 1000:1000 ./data` once.
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

To add another translation beyond BSB and KJV, write or use a parser that
converts the source into the canonical JSON format
(`backend/soap_journal/parsers/schema.py`), then load it:

```bash
python -m soap_journal.parsers.<translation> path/to/source --out data/translations/<code>.json
python -m soap_journal.cli load-translation data/translations/<code>.json
```

The side-by-side comparison view in the reader is active whenever two or more translations are loaded.

### NKJV

An NKJV parser is included. If you have the 1982 NKJV PDF, place it in
the `bibles/` directory and follow the instructions in
[`bibles/README.md`](bibles/README.md).

**Note on copyright:** only translations you have the legal right to redistribute should be loaded onto a publicly-accessible instance. The BSB is permissively licensed; many modern translations (ESV, NIV, NASB, etc.) are not. Loading a copyrighted translation onto a server you control for personal use is between you and the publisher.

## Manual install (without Docker)

Docker is the recommended path. If you can't or won't run Docker, you can
install the pieces directly:

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m soap_journal.parsers.bsb ../bible-sources/bsb/bsb.txt --out /tmp/bsb.json
python -m soap_journal.cli load-translation /tmp/bsb.json

# Frontend
cd ../frontend
npm ci
npm run build

# Run (backend serves the built frontend)
cd ../backend
FRONTEND_DIST_DIR=../frontend/dist DATA_DIR=./data \
    uvicorn soap_journal.main:create_app --factory --host 0.0.0.0 --port 8045
```

## Development

See `SPEC.md` for the full specification and `CLAUDE.md` for engineering conventions.

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

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for development setup, branch
conventions, and the project's philosophy on scope.

## Changelog

Release notes live in [`CHANGELOG.md`](CHANGELOG.md).

## License

MIT — see [`LICENSE`](LICENSE). Third-party software notices live in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
