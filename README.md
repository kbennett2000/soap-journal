# soap-journal

A self-hosted, offline-first SOAP (Scripture, Observation, Application, Prayer) journaling app with an integrated Bible reader. Designed to run on a home Ubuntu server over your local LAN — no internet required after install.

**Status:** in development. Not yet released.

## Features

- SOAP-method journaling with auto-pulled Scripture text
- Built-in Bible reader (Berean Standard Bible bundled; more translations via a parser architecture)
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
- ~500 MB disk for the app and bundled Bible text

## Quick Start

```bash
git clone https://github.com/YOUR-USERNAME/soap-journal.git
cd soap-journal
cp .env.example .env
# Edit .env to set PORT and other options if you want
docker compose up -d
```

Open `http://<your-server-ip>:8080` from any device on your LAN. The first user to register becomes the admin.

## Configuration

All configuration lives in `.env`:

| Variable     | Default     | Description                                      |
| ------------ | ----------- | ------------------------------------------------ |
| `PORT`       | `8080`      | Port the server listens on                       |
| `DATA_DIR`   | `./data`    | Where the SQLite DB and Bible files live         |
| `SECRET_KEY` | (generated) | Session signing key; auto-generated on first run |
| `BIND_HOST`  | `0.0.0.0`   | Interface to bind to                             |

Self-registration is controlled at runtime by the admin through the API
(`PUT /api/v1/admin/settings`). On a fresh install it defaults to off; the
first user to register becomes the admin and can flip it on for everyone else.

## Bundled Bible

This software bundles the **Berean Standard Bible (BSB)**, freely available
for use and redistribution from <https://bereanbible.com/>. The original
plain-text source and the BSB's attribution / public-domain notice live in
[`bible-sources/bsb/`](bible-sources/bsb/) — see
[`bible-sources/bsb/NOTICE`](bible-sources/bsb/NOTICE) for details.

To load the bundled BSB into your database on first install:

```bash
cd backend
alembic upgrade head
python -m soap_journal.parsers.bsb ../bible-sources/bsb/bsb.txt --out /tmp/bsb.json
python -m soap_journal.cli load-translation /tmp/bsb.json
```

## Adding a Bible Translation

To add another translation, write or use a parser that converts the source
into the canonical JSON format (`backend/soap_journal/parsers/schema.py`),
then load it:

```bash
python -m soap_journal.parsers.<translation> path/to/source --out data/translations/<code>.json
python -m soap_journal.cli load-translation data/translations/<code>.json
```

Once a second translation is loaded, the side-by-side comparison view in the reader becomes active.

**Note on copyright:** only translations you have the legal right to redistribute should be loaded onto a publicly-accessible instance. The BSB is permissively licensed; many modern translations (ESV, NIV, NASB, etc.) are not. Loading a copyrighted translation onto a server you control for personal use is between you and the publisher.

## Backing Up Your Data

Everything you care about is in the `DATA_DIR` (default `./data`). Copy that folder to back up. Restore by copying it back.

## Development

See `SPEC.md` for the full specification and `CLAUDE.md` for engineering conventions.

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn soap_journal.main:app --reload --port 8080

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## License

MIT — see `LICENSE`.
