"""Tag listing + autocomplete endpoints.

Tags are per-user and managed implicitly through entry saves (see
core/entries.py). These read-only endpoints power the dashboard's tag
list and the entry form's autocomplete dropdown.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.api.deps import get_current_user
from soap_journal.db.models.entry_tag import EntryTag
from soap_journal.db.models.tag import Tag
from soap_journal.db.models.user import User
from soap_journal.db.session import get_db
from soap_journal.schemas.entries import (
    TagAutocompleteResponse,
    TagListResponse,
    TagSummary,
)

router = APIRouter(
    prefix="/tags",
    tags=["tags"],
    dependencies=[Depends(get_current_user)],
)


def _summary(tag_id: int, name: str, count: int) -> TagSummary:
    return TagSummary(id=tag_id, name=name, entry_count=int(count))


@router.get("", response_model=TagListResponse)
async def list_tags(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TagListResponse:
    # Single grouped query: tags LEFT JOIN entry_tags, count per tag.
    rows = (
        await db.execute(
            select(Tag.id, Tag.name, func.count(EntryTag.entry_id))
            .join(EntryTag, EntryTag.tag_id == Tag.id, isouter=True)
            .where(Tag.user_id == user.id)
            .group_by(Tag.id)
            .order_by(func.lower(Tag.name).asc())
        )
    ).all()
    return TagListResponse(tags=[_summary(*r) for r in rows])


@router.get("/autocomplete", response_model=TagAutocompleteResponse)
async def autocomplete_tags(
    q: Annotated[str, Query(min_length=1)],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TagAutocompleteResponse:
    needle = q.strip().lower()
    if not needle:
        # FastAPI's min_length=1 catches the all-empty case, but a
        # whitespace-only `q` still gets here.
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "type": "string_too_short",
                    "loc": ["query", "q"],
                    "msg": "query must not be whitespace-only",
                }
            ],
        )

    rows = (
        await db.execute(
            select(Tag.id, Tag.name, func.count(EntryTag.entry_id))
            .join(EntryTag, EntryTag.tag_id == Tag.id, isouter=True)
            .where(
                Tag.user_id == user.id,
                Tag.name_lower.startswith(needle),
            )
            .group_by(Tag.id)
            .order_by(
                func.count(EntryTag.entry_id).desc(),
                func.lower(Tag.name).asc(),
            )
            .limit(10)
        )
    ).all()
    return TagAutocompleteResponse(tags=[_summary(*r) for r in rows])
