"""SOAP journal entry CRUD endpoints.

Every route requires `get_current_user` and scopes its queries to that
user's id — users can only see/edit/delete their own entries. Cross-user
access returns 404 (same response as not-found) so the API never leaks
the existence of other users' entries.

The save-time pipeline (parse reference, resolve translation, snapshot
verse text, rebuild link tables, resolve tags) lives in
`core/entries.py` and is shared by POST and PUT.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.api.deps import get_current_user
from soap_journal.core.entries import save_entry
from soap_journal.core.errors import ErrorCode, raise_http
from soap_journal.db.models.entry import Entry
from soap_journal.db.models.entry_tag import EntryTag
from soap_journal.db.models.tag import Tag
from soap_journal.db.models.translation import Translation
from soap_journal.db.models.user import User
from soap_journal.db.session import get_db
from soap_journal.schemas.entries import (
    EntryCreateRequest,
    EntryEnvelope,
    EntryListOrder,
    EntryListResponse,
    EntryResponse,
    EntryTagSummary,
    EntryUpdateRequest,
)

router = APIRouter(
    prefix="/entries",
    tags=["entries"],
    dependencies=[Depends(get_current_user)],
)


# ---- response building -----------------------------------------------------


async def _build_response(db: AsyncSession, entry: Entry) -> EntryResponse:
    translation_code = (
        await db.execute(
            select(Translation.code).where(Translation.id == entry.scripture_translation_id)
        )
    ).scalar_one()

    tag_rows = (
        (
            await db.execute(
                select(Tag)
                .join(EntryTag, EntryTag.tag_id == Tag.id)
                .where(EntryTag.entry_id == entry.id)
                .order_by(func.lower(Tag.name).asc())
            )
        )
        .scalars()
        .all()
    )
    tags = [EntryTagSummary(id=t.id, name=t.name) for t in tag_rows]

    title = (entry.title or "").strip() or None
    display_title = title if title else entry.scripture_ref

    return EntryResponse(
        id=entry.id,
        title=title,
        display_title=display_title,
        entry_date=entry.entry_date,
        scripture_ref=entry.scripture_ref,
        translation_code=translation_code,
        scripture_text=entry.scripture_text,
        observation=entry.observation,
        application=entry.application,
        prayer=entry.prayer,
        tags=tags,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


# ---- lookup helpers --------------------------------------------------------


async def _own_entry_or_404(
    db: AsyncSession, user_id: int, entry_id: int
) -> Entry:
    entry = await db.get(Entry, entry_id)
    if entry is None or entry.user_id != user_id:
        raise_http(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.ENTRY_NOT_FOUND,
            f"entry {entry_id} not found",
        )
    return entry


# ---- endpoints -------------------------------------------------------------


@router.post(
    "",
    response_model=EntryEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_entry(
    body: EntryCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EntryEnvelope:
    entry = await save_entry(
        db,
        user_id=user.id,
        title=body.title,
        entry_date_value=body.entry_date,
        scripture_ref=body.scripture_ref,
        translation_code=body.translation_code,
        observation=body.observation,
        application=body.application,
        prayer=body.prayer,
        tag_names=body.tags,
    )
    await db.commit()
    await db.refresh(entry)
    return EntryEnvelope(entry=await _build_response(db, entry))


@router.get("", response_model=EntryListResponse)
async def list_entries(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    order: EntryListOrder = "newest",
) -> EntryListResponse:
    total = (
        await db.execute(
            select(func.count(Entry.id)).where(Entry.user_id == user.id)
        )
    ).scalar_one()

    direction_asc = order == "oldest"
    if direction_asc:
        ordering = (Entry.entry_date.asc(), Entry.created_at.asc(), Entry.id.asc())
    else:
        ordering = (Entry.entry_date.desc(), Entry.created_at.desc(), Entry.id.desc())

    rows = (
        (
            await db.execute(
                select(Entry)
                .where(Entry.user_id == user.id)
                .order_by(*ordering)
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )

    entries = [await _build_response(db, entry) for entry in rows]
    return EntryListResponse(
        entries=entries, total=int(total), limit=limit, offset=offset
    )


@router.get("/{entry_id}", response_model=EntryEnvelope)
async def get_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EntryEnvelope:
    entry = await _own_entry_or_404(db, user.id, entry_id)
    return EntryEnvelope(entry=await _build_response(db, entry))


@router.put("/{entry_id}", response_model=EntryEnvelope)
async def update_entry(
    entry_id: int,
    body: EntryUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EntryEnvelope:
    entry = await _own_entry_or_404(db, user.id, entry_id)
    entry = await save_entry(
        db,
        user_id=user.id,
        title=body.title,
        entry_date_value=body.entry_date,
        scripture_ref=body.scripture_ref,
        translation_code=body.translation_code,
        observation=body.observation,
        application=body.application,
        prayer=body.prayer,
        tag_names=body.tags,
        existing=entry,
    )
    await db.commit()
    await db.refresh(entry)
    return EntryEnvelope(entry=await _build_response(db, entry))


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    entry = await _own_entry_or_404(db, user.id, entry_id)
    # SQLite cascade isn't enforced without PRAGMA; clear link tables
    # explicitly, matching the loader's pattern from the bible slice.
    from sqlalchemy import delete  # local import to keep top-level imports tidy

    from soap_journal.db.models.entry_scripture_verse import EntryScriptureVerse

    await db.execute(
        delete(EntryScriptureVerse)
        .where(EntryScriptureVerse.entry_id == entry.id)
        .execution_options(synchronize_session="fetch")
    )
    await db.execute(
        delete(EntryTag)
        .where(EntryTag.entry_id == entry.id)
        .execution_options(synchronize_session="fetch")
    )
    await db.delete(entry)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
