"""Response schemas for the Bible reader API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from soap_journal.schemas.entries import EntryResponse


class TranslationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    language: str
    copyright: str


class TranslationListResponse(BaseModel):
    translations: list[TranslationSummary]


class BookSummary(BaseModel):
    name: str
    abbreviation: str
    order_index: int
    testament: Literal["OT", "NT"]
    chapter_count: int


class TranslationDetailResponse(BaseModel):
    translation: TranslationSummary
    books: list[BookSummary]


# Typed translator-note categories (tn/sn/tc/map); None for a plain footnote.
# Declared locally to keep the response schema decoupled from the parser package.
NoteType = Literal["tn", "sn", "tc", "map"]


class CrossRefResponse(BaseModel):
    """A cross-reference from a note to a verse (or verse range) in the same translation."""

    to_book: str  # target book abbreviation (display label + navigable alias)
    to_chapter: int
    to_verse_start: int
    to_verse_end: int | None = None


class FootnoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    # Rich-note fields. Plain footnotes (the 13 bundled translations) default to
    # null/0/[] so clients branch on `note_type`.
    note_type: NoteType | None = None
    char_offset: int | None = None
    marker: int | None = None
    ordinal: int = 0
    cross_refs: list[CrossRefResponse] = []


class VerseResponse(BaseModel):
    id: int
    number: int
    text: str
    is_red_letter: bool
    footnotes: list[FootnoteResponse] = []


class HeadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    before_verse: int
    text: str


class ChapterPointer(BaseModel):
    book_name: str
    chapter_number: int


class ChapterResponse(BaseModel):
    translation_code: str
    book: BookSummary
    chapter_number: int
    verses: list[VerseResponse]
    headings: list[HeadingResponse]
    previous: ChapterPointer | None
    next: ChapterPointer | None


class ResolvedReference(BaseModel):
    canonical_string: str
    translation_code: str
    book: BookSummary
    chapter_number: int
    start_verse: int
    end_verse: int


class ResolvedReferenceResponse(BaseModel):
    reference: ResolvedReference
    verses: list[VerseResponse]


class PassageEntriesResponse(BaseModel):
    """Cross-references from a passage to the current user's entries."""

    reference: ResolvedReference
    count: int
    entries: list[EntryResponse]
