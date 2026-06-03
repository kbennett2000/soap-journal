"""Journal backup export endpoint.

``GET /backup/export`` streams the current user's journal as a
``soap-journal-backup`` v1 JSON file (see ``schemas/backup.py`` for the
contract). Export only — import/restore lives in a later cycle. The router is
gated by ``get_current_user`` so every request is scoped to one user.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.api.deps import get_current_user
from soap_journal.core.backup import build_backup
from soap_journal.db.models.user import User
from soap_journal.db.session import get_db

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
