"""Response schemas for the Bible reader API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


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


class FootnoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str


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
