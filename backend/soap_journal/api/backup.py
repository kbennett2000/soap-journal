"""Journal backup export + import endpoints.

``GET /backup/export`` streams the current user's journal as a
``soap-journal-backup`` v1 JSON file (see ``schemas/backup.py`` for the
contract). ``POST /backup/import`` is the reverse: it takes a backup file in the
raw request body, validates it fully *before* touching the DB, merges it via the
cycle-2a engine, and commits (or rolls back / dry-runs). The router is gated by
``get_current_user`` so every request is scoped to one user.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.api.deps import get_current_user
from soap_journal.core.backup import build_backup
from soap_journal.core.backup_import import import_backup, validate_backup_dates
from soap_journal.core.errors import ErrorCode, raise_http
from soap_journal.db.models.user import User
from soap_journal.db.session import get_db
from soap_journal.schemas.backup import BackupDocument, ImportReport

router = APIRouter(
    prefix="/backup",
    tags=["backup"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/export")
async def export_backup(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    now = datetime.now(UTC)
    document = await build_backup(db, user.id, now)
    filename = f"soap-journal-backup-{now.date().isoformat()}.json"
    return JSONResponse(
        content=document.model_dump(),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _summarize_validation_error(exc: ValidationError) -> str:
    """Condense a Pydantic ValidationError into a short, readable message."""
    parts: list[str] = []
    for err in exc.errors()[:3]:
        loc = ".".join(str(p) for p in err["loc"])
        parts.append(f"{loc}: {err['msg']}" if loc else err["msg"])
    return "; ".join(parts) or "invalid backup file"


@router.post("/import")
async def import_backup_endpoint(
    request: Request,
    dry_run: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ImportReport:
    # --- Validate-before-write: nothing mutates or commits until all of this
    # passes. A bad file changes nothing and never 500s. ---

    # 1. Raw bytes -> JSON.
    raw = await request.body()
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise_http(400, ErrorCode.INVALID_BACKUP, "file is not valid JSON")

    # 2. Version pre-check before Pydantic, so a newer file gives a friendly
    # message instead of a cryptic Literal[1] mismatch.
    version = parsed.get("version") if isinstance(parsed, dict) else None
    if isinstance(version, int) and version > 1:
        raise_http(
            400,
            ErrorCode.BACKUP_VERSION_UNSUPPORTED,
            "this backup is from a newer version of the app; update to import it",
        )

    # 3. Structural validation (catches extra keys, wrong format literal, wrong
    # version, missing fields, wrong types).
    try:
        document = BackupDocument.model_validate(parsed)
    except ValidationError as exc:
        raise_http(400, ErrorCode.INVALID_BACKUP, _summarize_validation_error(exc))

    # 4. Date/timestamp parseability (the schema types these as plain str).
    date_errors = validate_backup_dates(document)
    if date_errors:
        raise_http(400, ErrorCode.INVALID_BACKUP, date_errors[0])

    # --- Run the engine inside this request's transaction. ---
    try:
        report = await import_backup(db, user.id, document, dry_run=dry_run)
        if not dry_run:
            await db.commit()
        # dry_run wrote nothing, so there is nothing to undo: get_db closes the
        # session on request end, discarding the read-only transaction. (An
        # explicit rollback here is redundant in production and, under the test's
        # shared single-session fixture, would also wipe earlier-committed state.)
    except HTTPException:
        raise
    except Exception:
        await db.rollback()  # belt-and-suspenders: a failed import commits nothing
        raise
    return report
