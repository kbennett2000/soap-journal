"""Bible reader API.

Four endpoints, all authenticated:

  GET /translations                                         list loaded translations
  GET /translations/{code}                                  detail + book list + chapter counts
  GET /translations/{code}/books/{book_name}/chapters/{n}   full chapter content + nav
  GET /resolve?ref=...&translation=...                      jump-bar resolver

Query strategy (deliberate):

- Each endpoint runs a small fixed number of explicit SELECTs rather than
  leaning on ORM relationships. The chapter endpoint, for example: one
  SELECT for the chapter+book, one for the chapter's verses, one for its
  headings, one for footnotes-by-verse-id (joined to the chapter's verses),
  plus up to four small SELECTs for previous/next navigation (previous
  book + its max chapter; next book + its first chapter). No N+1.
- chapter_count for the translation-detail endpoint is a single
  `SELECT book.*, COUNT(chapters.id) GROUP BY book.id`. Verified by
  bible_test.py with sqlalchemy.event-based query counting.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.api.deps import get_current_user
from soap_journal.core.bible.books import get_book_by_name
from soap_journal.core.bible_search import run_search
from soap_journal.core.errors import ErrorCode, raise_http
from soap_journal.core.references import (
    ParsedReference,
    ReferenceParseError,
    parse_reference_or_raise,
)
from soap_journal.db.models.book import Book
from soap_journal.db.models.chapter import Chapter
from soap_journal.db.models.cross_reference import CrossReference
from soap_journal.db.models.entry import Entry
from soap_journal.db.models.entry_scripture_verse import EntryScriptureVerse
from soap_journal.db.models.entry_tag import EntryTag
from soap_journal.db.models.footnote import Footnote
from soap_journal.db.models.heading import Heading
from soap_journal.db.models.tag import Tag
from soap_journal.db.models.translation import Translation
from soap_journal.db.models.user import User
from soap_journal.db.models.verse import Verse
from soap_journal.db.session import get_db
from soap_journal.schemas.bible import (
    BookSummary,
    ChapterPointer,
    ChapterResponse,
    CrossRefResponse,
    FootnoteResponse,
    HeadingResponse,
    PassageEntriesResponse,
    ResolvedReference,
    ResolvedReferenceResponse,
    SearchResponse,
    SearchScope,
    TranslationDetailResponse,
    TranslationListResponse,
    TranslationSummary,
    VerseResponse,
)
from soap_journal.schemas.entries import EntryResponse, EntryTagSummary

router = APIRouter(
    prefix="/bible",
    tags=["bible"],
    # Bible reading is gated behind login: same as the rest of the app.
    dependencies=[Depends(get_current_user)],
)


# ---- helpers ---------------------------------------------------------------


def _translation_to_summary(row: Translation) -> TranslationSummary:
    return TranslationSummary(
        code=row.code,
        name=row.name,
        language=row.language,
        copyright=row.copyright_notice,
    )


def _testament_for(book_name: str) -> Literal["OT", "NT"]:
    canon = get_book_by_name(book_name)
    if canon is None:
        # The DB book row exists with a non-canonical name. Loader validates
        # against ALL_BOOKS, so this is a "shouldn't happen" — if it does,
        # default to OT and let an integration test fail loudly.
        return "OT"
    return canon.testament


async def _get_translation_by_code(db: AsyncSession, code: str) -> Translation:
    result = await db.execute(select(Translation).where(Translation.code == code))
    translation = result.scalar_one_or_none()
    if translation is None:
        raise_http(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.TRANSLATION_NOT_FOUND,
            f"translation {code!r} is not loaded",
        )
    return translation


async def _resolve_book(db: AsyncSession, translation_id: int, book_name_input: str) -> Book:
    """Resolve a user-supplied book name (any alias) to its DB row in this
    translation. 404s on either an unrecognized name or a translation that
    doesn't have the book loaded.
    """
    canon = get_book_by_name(book_name_input)
    if canon is None:
        raise_http(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.BOOK_NOT_FOUND,
            f"unknown book name: {book_name_input!r}",
        )
    result = await db.execute(
        select(Book).where(Book.translation_id == translation_id, Book.name == canon.name)
    )
    book = result.scalar_one_or_none()
    if book is None:
        raise_http(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.BOOK_NOT_FOUND,
            f"{canon.name!r} is not loaded for this translation",
        )
    return book


async def _get_chapter(db: AsyncSession, book_id: int, chapter_number: int) -> Chapter:
    result = await db.execute(
        select(Chapter).where(Chapter.book_id == book_id, Chapter.number == chapter_number)
    )
    chapter = result.scalar_one_or_none()
    if chapter is None:
        raise_http(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.CHAPTER_NOT_FOUND,
            f"chapter {chapter_number} not found",
        )
    return chapter


async def _verses_with_footnotes(db: AsyncSession, chapter_id: int) -> list[VerseResponse]:
    """Load a chapter's verses + their footnotes (with nested cross-refs).

    Fixed query budget, no N+1: one SELECT for verses, one for footnotes (by
    verse id), and — only when the chapter has footnotes — one for the
    cross-references (by footnote id, joined to `books` for the target
    abbreviation). Cross-refs are grouped under footnotes, footnotes under
    verses, in Python. Plain translations (no typed notes, no cross-refs) come
    back with the rich fields defaulted (null/0/[]).
    """
    verse_rows = (
        (
            await db.execute(
                select(Verse).where(Verse.chapter_id == chapter_id).order_by(Verse.number.asc())
            )
        )
        .scalars()
        .all()
    )
    if not verse_rows:
        return []

    verse_ids = [v.id for v in verse_rows]
    footnote_rows = (
        (
            await db.execute(
                select(Footnote)
                .where(Footnote.verse_id.in_(verse_ids))
                .order_by(Footnote.verse_id.asc(), Footnote.ordinal.asc(), Footnote.id.asc())
            )
        )
        .scalars()
        .all()
    )

    # One cross-ref query for the whole chapter, joined to books for the target
    # abbreviation; skipped entirely when the chapter has no footnotes.
    cross_refs_by_footnote: dict[int, list[CrossRefResponse]] = {}
    footnote_ids = [fn.id for fn in footnote_rows]
    if footnote_ids:
        xref_rows = (
            await db.execute(
                select(CrossReference, Book.abbreviation)
                .join(Book, Book.id == CrossReference.to_book_id)
                .where(CrossReference.footnote_id.in_(footnote_ids))
                .order_by(CrossReference.id.asc())
            )
        ).all()
        for xref, to_book_abbreviation in xref_rows:
            cross_refs_by_footnote.setdefault(xref.footnote_id, []).append(
                CrossRefResponse(
                    to_book=to_book_abbreviation,
                    to_chapter=xref.to_chapter,
                    to_verse_start=xref.to_verse_start,
                    to_verse_end=xref.to_verse_end,
                )
            )

    footnotes_by_verse: dict[int, list[FootnoteResponse]] = {}
    for fn in footnote_rows:
        footnotes_by_verse.setdefault(fn.verse_id, []).append(
            FootnoteResponse(
                id=fn.id,
                text=fn.text,
                note_type=fn.note_type,
                char_offset=fn.char_offset,
                marker=fn.marker,
                ordinal=fn.ordinal,
                cross_refs=cross_refs_by_footnote.get(fn.id, []),
            )
        )

    return [
        VerseResponse(
            id=v.id,
            number=v.number,
            text=v.text,
            is_red_letter=v.is_red_letter,
            footnotes=footnotes_by_verse.get(v.id, []),
        )
        for v in verse_rows
    ]


async def _headings(db: AsyncSession, chapter_id: int) -> list[HeadingResponse]:
    rows = (
        (
            await db.execute(
                select(Heading)
                .where(Heading.chapter_id == chapter_id)
                .order_by(Heading.before_verse.asc(), Heading.id.asc())
            )
        )
        .scalars()
        .all()
    )
    return [HeadingResponse.model_validate(r) for r in rows]


async def _book_with_chapter_count(db: AsyncSession, book: Book) -> BookSummary:
    count = (
        await db.execute(select(func.count(Chapter.id)).where(Chapter.book_id == book.id))
    ).scalar_one()
    return BookSummary(
        name=book.name,
        abbreviation=book.abbreviation,
        order_index=book.order_index,
        testament=_testament_for(book.name),
        chapter_count=int(count),
    )


async def _previous_pointer(
    db: AsyncSession, translation_id: int, book: Book, chapter_number: int
) -> ChapterPointer | None:
    if chapter_number > 1:
        return ChapterPointer(book_name=book.name, chapter_number=chapter_number - 1)
    # First chapter of this book — back up to the previous book in this
    # translation by order_index and find its highest chapter number.
    prev_book = (
        await db.execute(
            select(Book)
            .where(
                Book.translation_id == translation_id,
                Book.order_index < book.order_index,
            )
            .order_by(Book.order_index.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if prev_book is None:
        return None
    last_chapter = (
        await db.execute(select(func.max(Chapter.number)).where(Chapter.book_id == prev_book.id))
    ).scalar_one()
    if last_chapter is None:
        return None
    return ChapterPointer(book_name=prev_book.name, chapter_number=int(last_chapter))


async def _next_pointer(
    db: AsyncSession,
    translation_id: int,
    book: Book,
    chapter_number: int,
    max_chapter: int,
) -> ChapterPointer | None:
    if chapter_number < max_chapter:
        return ChapterPointer(book_name=book.name, chapter_number=chapter_number + 1)
    next_book = (
        await db.execute(
            select(Book)
            .where(
                Book.translation_id == translation_id,
                Book.order_index > book.order_index,
            )
            .order_by(Book.order_index.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if next_book is None:
        return None
    first_chapter_exists = (
        await db.execute(
            select(Chapter.number)
            .where(Chapter.book_id == next_book.id)
            .order_by(Chapter.number.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if first_chapter_exists is None:
        return None
    return ChapterPointer(book_name=next_book.name, chapter_number=int(first_chapter_exists))


async def _default_translation(db: AsyncSession) -> Translation:
    """Resolve `?translation=` default: the first-loaded translation."""
    result = await db.execute(
        select(Translation).order_by(Translation.loaded_at.asc(), Translation.id.asc()).limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise_http(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.TRANSLATION_NOT_FOUND,
            "no translations are loaded",
        )
    return row


# ---- endpoints -------------------------------------------------------------


@router.get("/translations", response_model=TranslationListResponse)
async def list_translations(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> TranslationListResponse:
    rows = (
        (
            await db.execute(
                select(Translation).order_by(Translation.loaded_at.asc(), Translation.id.asc())
            )
        )
        .scalars()
        .all()
    )
    return TranslationListResponse(translations=[_translation_to_summary(t) for t in rows])


@router.get("/translations/{code}", response_model=TranslationDetailResponse)
async def get_translation(
    code: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> TranslationDetailResponse:
    translation = await _get_translation_by_code(db, code)

    # One grouped query for books-with-chapter-counts; no N+1.
    rows = (
        await db.execute(
            select(Book, func.count(Chapter.id))
            .join(Chapter, Chapter.book_id == Book.id, isouter=True)
            .where(Book.translation_id == translation.id)
            .group_by(Book.id)
            .order_by(Book.order_index.asc())
        )
    ).all()

    books = [
        BookSummary(
            name=book.name,
            abbreviation=book.abbreviation,
            order_index=book.order_index,
            testament=_testament_for(book.name),
            chapter_count=int(count),
        )
        for book, count in rows
    ]

    return TranslationDetailResponse(
        translation=_translation_to_summary(translation),
        books=books,
    )


@router.get(
    "/translations/{code}/books/{book_name}/chapters/{chapter_number}",
    response_model=ChapterResponse,
)
async def get_chapter(
    code: str,
    book_name: str,
    chapter_number: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ChapterResponse:
    if chapter_number < 1:
        raise_http(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.CHAPTER_NOT_FOUND,
            f"chapter {chapter_number} not found",
        )

    translation = await _get_translation_by_code(db, code)
    book = await _resolve_book(db, translation.id, book_name)
    chapter = await _get_chapter(db, book.id, chapter_number)

    verses = await _verses_with_footnotes(db, chapter.id)
    headings = await _headings(db, chapter.id)
    book_summary = await _book_with_chapter_count(db, book)

    prev_ptr = await _previous_pointer(db, translation.id, book, chapter_number)
    next_ptr = await _next_pointer(
        db, translation.id, book, chapter_number, book_summary.chapter_count
    )

    return ChapterResponse(
        translation_code=translation.code,
        book=book_summary,
        chapter_number=chapter_number,
        verses=verses,
        headings=headings,
        previous=prev_ptr,
        next=next_ptr,
    )


@router.get("/resolve", response_model=ResolvedReferenceResponse)
async def resolve_reference(
    ref: str,
    translation: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ResolvedReferenceResponse:
    try:
        parsed: ParsedReference = parse_reference_or_raise(ref)
    except ReferenceParseError as exc:
        raise_http(status.HTTP_400_BAD_REQUEST, ErrorCode.INVALID_REFERENCE, str(exc))

    translation_row = (
        await _get_translation_by_code(db, translation)
        if translation is not None
        else await _default_translation(db)
    )
    book = await _resolve_book(db, translation_row.id, parsed.book.name)
    chapter = await _get_chapter(db, book.id, parsed.chapter)

    all_verses = await _verses_with_footnotes(db, chapter.id)
    if not all_verses:
        raise_http(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.CHAPTER_NOT_FOUND,
            f"chapter {parsed.chapter} has no verses",
        )

    last_verse_number = all_verses[-1].number

    if parsed.start_verse is None:
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
    book_summary = await _book_with_chapter_count(db, book)

    return ResolvedReferenceResponse(
        reference=ResolvedReference(
            canonical_string=parsed.canonical_string,
            translation_code=translation_row.code,
            book=book_summary,
            chapter_number=parsed.chapter,
            start_verse=start,
            end_verse=end,
        ),
        verses=selected,
    )


# ---- full-text search ------------------------------------------------------


@router.get("/search", response_model=SearchResponse)
async def search_scripture(
    q: Annotated[str, Query(min_length=1)],
    translation: str | None = None,
    scope: SearchScope = "both",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> SearchResponse:
    """Full-text search over verse text and translator's notes (FTS5, bm25).

    Searches a single translation: the one named by `translation` (a code), or
    the first-loaded translation by default — mirroring the reader. Verse and
    note hits come back as separate ranked lists with highlighted snippets.
    Note hits exist only where the translation has notes (i.e. NET); for a
    translation without notes the note list is simply empty.
    """
    translation_row = (
        await _get_translation_by_code(db, translation)
        if translation is not None
        else await _default_translation(db)
    )
    return await run_search(
        db,
        q=q,
        translation_code=translation_row.code,
        translation_id=translation_row.id,
        scope=scope,
        limit=limit,
        offset=offset,
    )


# ---- passage -> entries (cross-references) --------------------------------


@router.get("/passages/entries", response_model=PassageEntriesResponse)
async def passage_entries(
    ref: str,
    translation: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PassageEntriesResponse:
    """Return the current user's entries whose verse linkage overlaps the
    requested passage.

    Query budget: 4 SELECTs.
      1. Translation by code (or default).
      2. One LEFT-JOINed query covering: book + correlated chapter_count
         + the requested chapter + every verse in it. NULL columns
         disambiguate "book missing" vs "chapter missing" without
         separate lookups.
      3. Entries (current user only) joined with translations.code.
      4. Tags for the matching entries, batched IN(...).

    Cross-translation matching is intentionally out of scope: verse_id
    differs across translations, so an entry created against (say) the
    NKJV won't match a BSB query even if the book/chapter/verse tuple
    is the same. See backend/README.md "Passage cross-references".
    """
    try:
        parsed: ParsedReference = parse_reference_or_raise(ref)
    except ReferenceParseError as exc:
        raise_http(status.HTTP_400_BAD_REQUEST, ErrorCode.INVALID_REFERENCE, str(exc))

    # Query 1: translation row (with TRANSLATION_NOT_FOUND specificity).
    translation_row = (
        await _get_translation_by_code(db, translation)
        if translation is not None
        else await _default_translation(db)
    )

    canon_book = get_book_by_name(parsed.book.name)
    assert canon_book is not None  # parser already resolved it

    # Query 2: combined book + chapter + verses + chapter_count.
    chapter_count_subq = (
        select(func.count(Chapter.id))
        .where(Chapter.book_id == Book.id)
        .correlate(Book)
        .scalar_subquery()
    )
    combined_rows = (
        await db.execute(
            select(
                Book.id.label("book_id"),
                Book.name.label("book_name"),
                Book.abbreviation.label("book_abbrev"),
                Book.order_index.label("book_order"),
                chapter_count_subq.label("chapter_count"),
                Chapter.id.label("chapter_id"),
                Verse.id.label("verse_id"),
                Verse.number.label("verse_number"),
            )
            .select_from(Book)
            .outerjoin(
                Chapter,
                and_(Chapter.book_id == Book.id, Chapter.number == parsed.chapter),
            )
            .outerjoin(Verse, Verse.chapter_id == Chapter.id)
            .where(
                Book.translation_id == translation_row.id,
                Book.name == canon_book.name,
            )
            .order_by(Verse.number.asc())
        )
    ).all()

    if not combined_rows:
        raise_http(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.BOOK_NOT_FOUND,
            f"{canon_book.name!r} is not loaded for translation {translation_row.code!r}",
        )
    first = combined_rows[0]
    if first.chapter_id is None:
        raise_http(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.CHAPTER_NOT_FOUND,
            f"chapter {parsed.chapter} not found in {canon_book.name}",
        )
    if first.verse_id is None:
        # Chapter exists but has zero verses — shouldn't happen for BSB,
        # but the range check below would deadlock without a guard.
        raise_http(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.CHAPTER_NOT_FOUND,
            f"chapter {parsed.chapter} has no verses",
        )

    last_verse_number = combined_rows[-1].verse_number
    if parsed.start_verse is None:
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

    target_verse_ids = [row.verse_id for row in combined_rows if start <= row.verse_number <= end]
    book_summary = BookSummary(
        name=first.book_name,
        abbreviation=first.book_abbrev,
        order_index=first.book_order,
        testament=_testament_for(first.book_name),
        chapter_count=int(first.chapter_count),
    )

    if not target_verse_ids:
        # Defensive; shouldn't happen given the range check above.
        return PassageEntriesResponse(
            reference=ResolvedReference(
                canonical_string=parsed.canonical_string,
                translation_code=translation_row.code,
                book=book_summary,
                chapter_number=parsed.chapter,
                start_verse=start,
                end_verse=end,
            ),
            count=0,
            entries=[],
        )

    # Query 3: entries (this user only) with translations.code joined.
    page_rows = (
        await db.execute(
            select(Entry, Translation.code)
            .join(Translation, Translation.id == Entry.scripture_translation_id)
            .where(
                Entry.user_id == user.id,
                Entry.id.in_(
                    select(EntryScriptureVerse.entry_id)
                    .where(EntryScriptureVerse.verse_id.in_(target_verse_ids))
                    .distinct()
                ),
            )
            .order_by(
                Entry.entry_date.desc(),
                Entry.created_at.desc(),
                Entry.id.desc(),
            )
        )
    ).all()
    entry_rows = [row[0] for row in page_rows]
    translation_codes = {row[0].scripture_translation_id: row[1] for row in page_rows}

    # Batch tags for the page.
    entries: list[EntryResponse] = []
    if entry_rows:
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

        for entry in entry_rows:
            title = (entry.title or "").strip() or None
            display_title = title if title else entry.scripture_ref
            entries.append(
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

    return PassageEntriesResponse(
        reference=ResolvedReference(
            canonical_string=parsed.canonical_string,
            translation_code=translation_row.code,
            book=book_summary,
            chapter_number=parsed.chapter,
            start_verse=start,
            end_verse=end,
        ),
        count=len(entries),
        entries=entries,
    )
