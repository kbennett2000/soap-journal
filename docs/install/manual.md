# Advanced — installing soap-journal without Docker (Linux / macOS)

> ⚠️ **Most people should not use this guide.** Docker is the recommended path and
> is far easier to install, run, and update — start at the
> [install hub](README.md) and pick your platform. This page is for advanced users
> on Linux or macOS who have a specific reason to avoid Docker and are comfortable
> in a terminal. (On **Windows** without Docker, see the
> [advanced Windows guide](windows-manual.md) instead.)

Without Docker you install and run each piece yourself: a Python backend, a
built frontend it serves, and the bundled Bible text loaded by hand. There's no
container managing it, so starting it is a command you run, and it keeps running
only while that terminal stays open.

You'll need **Python 3.12+** and **Node 20+** installed and on your `PATH`.

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

Then open `http://localhost:8045` and register the first user — that account
becomes the administrator.

> Loading the user-supplied **NLT** or **NET** translations additionally needs
> `pdftotext` (from poppler) on your `PATH`: `brew install poppler` on macOS, or
> `sudo apt install poppler-utils` on Debian/Ubuntu. The 13 bundled translations
> above don't need it.

## Why Docker is still recommended

With this setup you're responsible for restarting the server after a reboot,
keeping Python and Node up to date, and re-running the build after an update
(`git pull`, then repeat the frontend build and restart the server). Docker
handles all of that and restarts soap-journal automatically. If this route gives
you trouble, the [Docker guides](README.md) are the smoother path.
