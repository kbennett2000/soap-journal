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

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.api.deps import get_current_user
from soap_journal.core.entries import save_entry
from soap_journal.core.entries_query import (
    AppliedFilterValues,
    apply_filters,
    resolve_filters,
)
from soap_journal.core.errors import ErrorCode, raise_http
from soap_journal.db.models.entry import Entry
from soap_journal.db.models.entry_tag import EntryTag
from soap_journal.db.models.tag import Tag
from soap_journal.db.models.translation import Translation
from soap_journal.db.models.user import User
from soap_journal.db.session import get_db
from soap_journal.schemas.entries import (
    AppliedFilters,
    CalendarDay,
    CalendarResponse,
    EntryCreateRequest,
    EntryEnvelope,
    EntryListOrder,
    EntryListResponse,
    EntryResponse,
    EntryTagSummary,
    EntryUpdateRequest,
    OnThisDayResponse,
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


async def _own_entry_or_404(db: AsyncSession, user_id: int, entry_id: int) -> Entry:
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


async def _build_entries_batch(
    db: AsyncSession, entry_rows: list[Entry], translation_codes: dict[int, str]
) -> list[EntryResponse]:
    """Build EntryResponse objects with one batched tag query for the whole page.

    `translation_codes` is the {translation_id -> code} map that the
    caller built in the page query (typically via a JOIN onto translations).
    """
    if not entry_rows:
        return []

    entry_ids = [e.id for e in entry_rows]
    tag_rows = (
        await db.execute(
            select(EntryTag.entry_id, Tag.id, Tag.name)
            .join(Tag, Tag.id == EntryTag.tag_id)
            .where(EntryTag.entry_id.in_(entry_ids))
            .order_by(EntryTag.entry_id, func.lower(Tag.name).asc())
        )
    ).all()
    tags_by_entry: dict[int, list[EntryTagSummary]] = {}
    for entry_id, tag_id, name in tag_rows:
        tags_by_entry.setdefault(entry_id, []).append(EntryTagSummary(id=tag_id, name=name))

    results: list[EntryResponse] = []
    for entry in entry_rows:
        title = (entry.title or "").strip() or None
        display_title = title if title else entry.scripture_ref
        results.append(
            EntryResponse(
                id=entry.id,
                title=title,
                display_title=display_title,
                entry_date=entry.entry_date,
                scripture_ref=entry.scripture_ref,
                translation_code=translation_codes[entry.scripture_translation_id],
                scripture_text=entry.scripture_text,
                observation=entry.observation,
                application=entry.application,
                prayer=entry.prayer,
                tags=tags_by_entry.get(entry.id, []),
                created_at=entry.created_at,
                updated_at=entry.updated_at,
            )
        )
    return results


def _applied_to_schema(applied: AppliedFilterValues) -> AppliedFilters:
    return AppliedFilters(
        q=applied.q,
        book=applied.book,
        tag=applied.tag,
        from_date=applied.from_date,
        to_date=applied.to_date,
    )


@router.get("", response_model=EntryListResponse)
async def list_entries(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    order: EntryListOrder = "newest",
    q: str | None = Query(default=None),
    book: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
) -> EntryListResponse:
    filters, applied = resolve_filters(q, book, tag, from_date, to_date)

    # Query 1: filtered total. The same WHERE goes on both selects via
    # apply_filters (EXISTS subqueries, no DISTINCT required).
    count_stmt = apply_filters(select(func.count(Entry.id)).select_from(Entry), user.id, filters)
    total = (await db.execute(count_stmt)).scalar_one()

    # Query 2: filtered page joined with translations.code so the response
    # builder doesn't have to look up translation_code per row.
    if order == "oldest":
        ordering = (Entry.entry_date.asc(), Entry.created_at.asc(), Entry.id.asc())
    else:
        ordering = (Entry.entry_date.desc(), Entry.created_at.desc(), Entry.id.desc())

    page_stmt = (
        apply_filters(select(Entry, Translation.code), user.id, filters)
        .join(Translation, Translation.id == Entry.scripture_translation_id)
        .order_by(*ordering)
        .limit(limit)
        .offset(offset)
    )
    page_rows = (await db.execute(page_stmt)).all()
    entry_rows = [row[0] for row in page_rows]
    translation_codes = {row[0].scripture_translation_id: row[1] for row in page_rows}

    # Query 3: tags for the page (batched IN(...)).
    entries = await _build_entries_batch(db, entry_rows, translation_codes)

    return EntryListResponse(
        entries=entries,
        total=int(total),
        limit=limit,
        offset=offset,
        applied_filters=_applied_to_schema(applied),
    )


# ---- calendar + on-this-day ------------------------------------------------


@router.get("/calendar", response_model=CalendarResponse)
async def calendar(
    year: Annotated[int, Query(ge=1900, le=2100)],
    month: Annotated[int, Query(ge=1, le=12)],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CalendarResponse:
    # One GROUP BY query against entries for this user/year/month.
    rows = (
        await db.execute(
            select(Entry.entry_date, func.count(Entry.id))
            .where(
                Entry.user_id == user.id,
                extract("year", Entry.entry_date) == year,
                extract("month", Entry.entry_date) == month,
            )
            .group_by(Entry.entry_date)
            .order_by(Entry.entry_date.asc())
        )
    ).all()

    days = [CalendarDay(entry_date=d, count=int(c)) for d, c in rows]
    total = sum(d.count for d in days)
    return CalendarResponse(year=year, month=month, days=days, total=total)


@router.get("/on-this-day", response_model=OnThisDayResponse)
async def on_this_day(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    date_value: Annotated[date | None, Query(alias="date")] = None,
    years_back: Annotated[int, Query(ge=1, le=50)] = 10,
) -> OnThisDayResponse:
    target = date_value or date.today()
    earliest_year = target.year - years_back

    # Match month + day + (year < target.year) + (year >= earliest_year).
    # Feb 29 behavior: target=Feb 29 leap year matches Feb 29 in prior
    # leap years; target=Feb 28 non-leap does NOT pull Feb 29 (because
    # day=28 != 29). See backend/README.md "On this day" notes.
    where_clauses = (
        Entry.user_id == user.id,
        extract("month", Entry.entry_date) == target.month,
        extract("day", Entry.entry_date) == target.day,
        extract("year", Entry.entry_date) < target.year,
        extract("year", Entry.entry_date) >= earliest_year,
    )

    page_rows = (
        await db.execute(
            select(Entry, Translation.code)
            .join(Translation, Translation.id == Entry.scripture_translation_id)
            .where(*where_clauses)
            .order_by(
                Entry.entry_date.desc(),
                Entry.created_at.desc(),
                Entry.id.desc(),
            )
        )
    ).all()
    entry_rows = [row[0] for row in page_rows]
    translation_codes = {row[0].scripture_translation_id: row[1] for row in page_rows}

    entries = await _build_entries_batch(db, entry_rows, translation_codes)
    return OnThisDayResponse(target_date=target, entries=entries)


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
