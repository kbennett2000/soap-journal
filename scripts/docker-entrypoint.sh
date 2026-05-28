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
# 3. Bootstrap all bundled translations. Each is checked and loaded
#    independently — a failure in one does not block the others.
#    Fully idempotent: already-loaded translations are skipped.
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

TOTAL=13
N=1

# ---- BSB bootstrap (text format, different parser) ----
BSB_SOURCE="/app/bible-sources/bsb/bsb.txt"
BSB_JSON="/tmp/bsb.json"

if [[ "$(translation_loaded BSB)" != "yes" ]]; then
    echo "[entrypoint] (${N}/${TOTAL}) parsing BSB..."
    python -m soap_journal.parsers.bsb "${BSB_SOURCE}" --out "${BSB_JSON}"
    echo "[entrypoint] (${N}/${TOTAL}) loading BSB into the database"
    python -m soap_journal.cli load-translation "${BSB_JSON}"
    rm -f "${BSB_JSON}"
    echo "[entrypoint] (${N}/${TOTAL}) BSB loaded"
else
    echo "[entrypoint] (${N}/${TOTAL}) BSB already loaded — skipping"
fi
N=$((N + 1))

# ---- PDFMaker-format translations bootstrap ----
# All PDFMaker-format translations share the same parser invocation
# pattern. Each is independent: a failure in one does not block others.
PDFMAKER_TRANSLATIONS="KJV AKJV ASV CPDV DBT DRB ERV JPS SLT WBT WEB YLT"

for CODE in ${PDFMAKER_TRANSLATIONS}; do
    LOWER_CODE=$(echo "${CODE}" | tr '[:upper:]' '[:lower:]')
    SOURCE="/app/bible-sources/${LOWER_CODE}/${LOWER_CODE}.pdf"
    JSON="/tmp/${LOWER_CODE}.json"

    if [[ "$(translation_loaded "${CODE}")" == "yes" ]]; then
        echo "[entrypoint] (${N}/${TOTAL}) ${CODE} already loaded — skipping"
    elif [[ ! -f "${SOURCE}" ]]; then
        echo "[entrypoint] (${N}/${TOTAL}) ${CODE} source not found — skipping"
    else
        echo "[entrypoint] (${N}/${TOTAL}) parsing ${CODE}..."
        if python -m "soap_journal.parsers.${LOWER_CODE}" "${SOURCE}" --out "${JSON}" \
           && python -m soap_journal.cli load-translation "${JSON}"; then
            echo "[entrypoint] (${N}/${TOTAL}) ${CODE} loaded"
        else
            echo "[entrypoint] WARNING: ${CODE} failed — continuing"
        fi
        rm -f "${JSON}"
    fi
    N=$((N + 1))
done

echo "[entrypoint] starting: $*"
exec "$@"
