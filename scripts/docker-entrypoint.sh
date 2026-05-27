#!/usr/bin/env bash
#
# soap-journal container bootstrap.
#
# Runs as root just long enough to fix bind-mount ownership on /data
# (Docker creates host-side bind-mount targets as root:root, which the
# unprivileged soap user can't write to). Then drops to soap via gosu
# before doing migrations, the BSB bootstrap, and exec'ing uvicorn.
#
# 1. chown /data to the soap user (idempotent).
# 2. Run pending Alembic migrations (fail fast if they error).
# 3. If no Bible translation is loaded yet, parse the bundled BSB source
#    into canonical JSON and load it into the database. Idempotent —
#    on subsequent boots this step is skipped.
# 4. exec the CMD so SIGTERM from `docker stop` reaches uvicorn directly.
#
set -euo pipefail

DATA_DIR="${DATA_DIR:-/data}"
RUN_AS="soap"

if [[ "$(id -u)" -eq 0 ]]; then
    chown -R "${RUN_AS}:${RUN_AS}" "${DATA_DIR}"
    # Re-exec this script as the unprivileged user so the rest of the
    # bootstrap (migrations, BSB load, uvicorn) never runs as root.
    exec gosu "${RUN_AS}" "$0" "$@"
fi

echo "[entrypoint] running as $(id -un) (uid $(id -u))"
echo "[entrypoint] data dir: ${DATA_DIR}"

BSB_SOURCE="/app/bible-sources/bsb/bsb.txt"
BSB_JSON="/tmp/bsb.json"

echo "[entrypoint] running alembic migrations"
alembic upgrade head

# Detect whether at least one translation is already loaded. We query the
# SQLite DB directly via Python's stdlib — no extra deps needed.
needs_load="$(
python - <<'PY'
import os, sqlite3
from pathlib import Path

db_path = Path(os.environ.get("DATA_DIR", "/data")) / "soap_journal.db"
if not db_path.exists():
    print("yes")
    raise SystemExit(0)

with sqlite3.connect(db_path) as conn:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='translations'"
    )
    if cur.fetchone() is None:
        print("yes")
    else:
        cur = conn.execute("SELECT COUNT(*) FROM translations")
        count = cur.fetchone()[0]
        print("no" if count > 0 else "yes")
PY
)"

if [[ "${needs_load}" == "yes" ]]; then
    echo "[entrypoint] no translations loaded — parsing bundled BSB"
    python -m soap_journal.parsers.bsb "${BSB_SOURCE}" --out "${BSB_JSON}"
    echo "[entrypoint] loading BSB into the database"
    python -m soap_journal.cli load-translation "${BSB_JSON}"
    rm -f "${BSB_JSON}"
else
    echo "[entrypoint] translations already loaded — skipping BSB bootstrap"
fi

echo "[entrypoint] starting: $*"
exec "$@"
