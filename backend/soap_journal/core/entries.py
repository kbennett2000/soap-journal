"""Save-time pipeline for SOAP journal entries.

Both `POST /entries` and `PUT /entries/{id}` route through `save_entry`,
which:

1. Parses the user's scripture reference via `parse_reference_or_raise`.
2. Resolves a translation (explicit `translation_code` or the
   first-loaded translation).
3. Resolves the book + chapter in that translation, validates the verse
   range against the chapter's actual length.
4. Snapshots the joined verse text into `entries.scripture_text` so a
   later translation reload can't mutate previously-written entries.
5. Replaces the entry's verse linkage rows in `entry_scripture_verses`.
6. Resolves the submitted tag names — case-insensitive lookup against
   the user's existing tags, create new ones with the user's casing
   when not found — and replaces the entry's `entry_tags` rows.

The whole pipeline runs inside the caller's transaction. The caller
(the API endpoint) is responsible for `commit()` / `rollback()`.
Raising any `HTTPException` here will roll the transaction back via
FastAPI's standard error handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from fastapi import status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.core.bible.books import get_book_by_name
from soap_journal.core.errors import ErrorCode, raise_http
from soap_journal.core.references import (
    ReferenceParseError,
    parse_reference_or_raise,
)
from soap_journal.db.models.book import Book
from soap_journal.db.models.chapter import Chapter
from soap_journal.db.models.entry import Entry
from soap_journal.db.models.entry_scripture_verse import EntryScriptureVerse
from soap_journal.db.models.entry_tag import EntryTag
from soap_journal.db.models.tag import Tag
from soap_journal.db.models.translation import Translation
from soap_journal.db.models.verse import Verse


@dataclass(slots=True)
class _Resolved:
    canonical_string: str
    translation: Translation
    verses: list[Verse]


async def _resolve_translation(db: AsyncSession, code: str | None) -> Translation:
    if code is not None:
        row = (
            await db.execute(select(Translation).where(Translation.code == code))
        ).scalar_one_or_none()
        if row is None:
            raise_http(
                status.HTTP_404_NOT_FOUND,
                ErrorCode.TRANSLATION_NOT_FOUND,
                f"translation {code!r} is not loaded",
            )
        return row
    row = (
        await db.execute(
            select(Translation).order_by(Translation.loaded_at.asc(), Translation.id.asc()).limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        raise_http(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.TRANSLATION_NOT_FOUND,
            "no translations are loaded",
        )
    return row


async def _resolve_scripture(
    db: AsyncSession, scripture_ref: str, translation_code: str | None
) -> _Resolved:
    try:
        parsed = parse_reference_or_raise(scripture_ref)
    except ReferenceParseError as exc:
        raise_http(status.HTTP_400_BAD_REQUEST, ErrorCode.INVALID_REFERENCE, str(exc))

    translation = await _resolve_translation(db, translation_code)

    canon_book = get_book_by_name(parsed.book.name)  # always succeeds — parser already resolved it
    assert canon_book is not None  # for type narrowing

    book = (
        await db.execute(
            select(Book).where(Book.translation_id == translation.id, Book.name == canon_book.name)
        )
    ).scalar_one_or_none()
    if book is None:
        raise_http(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.BOOK_NOT_FOUND,
            f"{canon_book.name!r} is not loaded for translation {translation.code!r}",
        )

    chapter = (
        await db.execute(
            select(Chapter).where(Chapter.book_id == book.id, Chapter.number == parsed.chapter)
        )
    ).scalar_one_or_none()
    if chapter is None:
        raise_http(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.CHAPTER_NOT_FOUND,
            f"chapter {parsed.chapter} not found in {canon_book.name}",
        )

    all_verses = (
        (
            await db.execute(
                select(Verse).where(Verse.chapter_id == chapter.id).order_by(Verse.number.asc())
            )
        )
        .scalars()
        .all()
    )
    if not all_verses:
        raise_http(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.CHAPTER_NOT_FOUND,
            f"chapter {parsed.chapter} has no verses",
        )

    last_verse_number = all_verses[-1].number
    if parsed.start_verse is None:
        # Whole-chapter reference: keep canonical_string as "Book N", but
        # the linked verses are 1..last.
        start, end = 1, last_verse_number
    else:
        start = parsed.start_verse
        end = parsed.end_verse if parsed.end_verse is not None else start
        if start > last_verse_number or end > last_verse_number:
            raise_http(
                status.HTTP_404_NOT_FOUND,
                ErrorCode.REFERENCE_OUT_OF_RANGE,
                f"chapter has {last_verse_number} verses; reference asked for {start}-{end}",
            )

    selected = [v for v in all_verses if start <= v.number <= end]
    return _Resolved(
        canonical_string=parsed.canonical_string,
        translation=translation,
        verses=list(selected),
    )


async def resolve_tags(db: AsyncSession, user_id: int, names: list[str]) -> list[Tag]:
    """Resolve user-supplied tag names to Tag rows for this user.

    - Deduplicates within `names` case-insensitively (first occurrence's
      casing wins for any new tags).
    - Looks up existing tags case-insensitively via the `name_lower`
      generated column.
    - Creates missing tags with the user's casing.
    - Returns tags in the order they first appeared in `names`.
    """
    seen: dict[str, str] = {}
    for raw in names:
        # Schema already trimmed/validated; defend anyway.
        stripped = raw.strip()
        if not stripped:
            continue
        key = stripped.lower()
        if key not in seen:
            seen[key] = stripped

    if not seen:
        return []

    keys = list(seen.keys())
    existing = (
        (await db.execute(select(Tag).where(Tag.user_id == user_id, Tag.name_lower.in_(keys))))
        .scalars()
        .all()
    )
    by_lower: dict[str, Tag] = {tag.name_lower: tag for tag in existing}

    resolved: list[Tag] = []
    for key in keys:
        tag = by_lower.get(key)
        if tag is None:
            tag = Tag(user_id=user_id, name=seen[key])
            db.add(tag)
        resolved.append(tag)
    await db.flush()
    return resolved


async def save_entry(
    db: AsyncSession,
    user_id: int,
    *,
    title: str | None,
    entry_date_value: date | None,
    scripture_ref: str,
    translation_code: str | None,
    observation: str,
    application: str,
    prayer: str,
    tag_names: list[str],
    existing: Entry | None = None,
) -> Entry:
    """Create or replace a SOAP entry. The caller commits the transaction."""
    resolved = await _resolve_scripture(db, scripture_ref, translation_code)
    scripture_text = " ".join(v.text for v in resolved.verses)
    chosen_date = entry_date_value or date.today()

    if existing is None:
        entry = Entry(user_id=user_id)
        db.add(entry)
    else:
        entry = existing

    entry.title = title
    entry.entry_date = chosen_date
    entry.scripture_ref = resolved.canonical_string
    entry.scripture_translation_id = resolved.translation.id
    entry.scripture_text = scripture_text
    entry.observation = observation
    entry.application = application
    entry.prayer = prayer
    await db.flush()  # need entry.id for the link tables

    # Rebuild verse links. The link table is per-entry small; delete-all-
    # then-insert is simpler than diffing.
    await db.execute(
        delete(EntryScriptureVerse)
        .where(EntryScriptureVerse.entry_id == entry.id)
        .execution_options(synchronize_session="fetch")
    )
    for verse in resolved.verses:
        db.add(EntryScriptureVerse(entry_id=entry.id, verse_id=verse.id))

    # Rebuild tag links. Orphaned Tag rows stay around per spec (so they
    # keep autocompleting).
    tags = await resolve_tags(db, user_id, tag_names)
    await db.execute(
        delete(EntryTag)
        .where(EntryTag.entry_id == entry.id)
        .execution_options(synchronize_session="fetch")
    )
    for tag in tags:
        db.add(EntryTag(entry_id=entry.id, tag_id=tag.id))

    await db.flush()
    return entry
