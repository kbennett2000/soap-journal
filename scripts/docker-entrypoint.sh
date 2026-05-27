#!/usr/bin/env bash
#
# soap-journal container bootstrap.
#
# Runs as root just long enough to fix bind-mount ownership on /data
# (Docker creates host-side bind-mount targets as root:root, which the
# unprivileged soap user can't write to). Then drops to soap via gosu
# before doing migrations, the translation bootstrap, and exec'ing uvicorn.
#
# 1. chown /data to the soap user (idempotent).
# 2. Run pending Alembic migrations (fail fast if they error).
# 3. Bootstrap bundled translations (BSB and KJV). Each is checked and
#    loaded independently — if BSB is already present but KJV is not,
#    only KJV is parsed and loaded. Fully idempotent.
# 4. exec the CMD so SIGTERM from `docker stop` reaches uvicorn directly.
#
set -euo pipefail

DATA_DIR="${DATA_DIR:-/data}"
RUN_AS="soap"

if [[ "$(id -u)" -eq 0 ]]; then
    chown -R "${RUN_AS}:${RUN_AS}" "${DATA_DIR}"
    # Re-exec this script as the unprivileged user so the rest of the
    # bootstrap (migrations, translation load, uvicorn) never runs as root.
    exec gosu "${RUN_AS}" "$0" "$@"
fi

echo "[entrypoint] running as $(id -un) (uid $(id -u))"
echo "[entrypoint] data dir: ${DATA_DIR}"

echo "[entrypoint] running alembic migrations"
alembic upgrade head

# Check whether a specific translation (by code) is already in the DB.
# Queries SQLite directly via Python's stdlib — no extra deps needed.
translation_loaded() {
    local code="$1"
    python - "$code" <<'PY'
import os, sqlite3, sys
from pathlib import Path

code = sys.argv[1]
db_path = Path(os.environ.get("DATA_DIR", "/data")) / "soap_journal.db"
if not db_path.exists():
    print("no"); raise SystemExit(0)

with sqlite3.connect(db_path) as conn:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='translations'"
    )
    if cur.fetchone() is None:
        print("no"); raise SystemExit(0)
    cur = conn.execute("SELECT COUNT(*) FROM translations WHERE code=?", (code,))
    print("yes" if cur.fetchone()[0] > 0 else "no")
PY
}

# ---- BSB bootstrap ----
BSB_SOURCE="/app/bible-sources/bsb/bsb.txt"
BSB_JSON="/tmp/bsb.json"

if [[ "$(translation_loaded BSB)" != "yes" ]]; then
    echo "[entrypoint] parsing bundled BSB"
    python -m soap_journal.parsers.bsb "${BSB_SOURCE}" --out "${BSB_JSON}"
    echo "[entrypoint] loading BSB into the database"
    python -m soap_journal.cli load-translation "${BSB_JSON}"
    rm -f "${BSB_JSON}"
else
    echo "[entrypoint] BSB already loaded — skipping"
fi

# ---- KJV bootstrap ----
KJV_SOURCE="/app/bible-sources/kjv/kjv.pdf"
KJV_JSON="/tmp/kjv.json"

if [[ "$(translation_loaded KJV)" != "yes" ]]; then
    if [[ -f "${KJV_SOURCE}" ]]; then
        echo "[entrypoint] parsing bundled KJV"
        python -m soap_journal.parsers.kjv "${KJV_SOURCE}" --out "${KJV_JSON}"
        echo "[entrypoint] loading KJV into the database"
        python -m soap_journal.cli load-translation "${KJV_JSON}"
        rm -f "${KJV_JSON}"
    else
        echo "[entrypoint] KJV source not found at ${KJV_SOURCE} — skipping"
    fi
else
    echo "[entrypoint] KJV already loaded — skipping"
fi

echo "[entrypoint] starting: $*"
exec "$@"
