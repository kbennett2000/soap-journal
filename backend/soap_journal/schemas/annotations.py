"""Pydantic request/response schemas for annotations (highlights)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from soap_journal.core.bible.books import get_book_by_name

HighlightColor = Literal["yellow", "green", "blue", "pink", "orange", "purple"]


def _canonical_book(value: str) -> str:
    book = get_book_by_name(value)
    if book is None:
        raise ValueError(f"unknown book: {value!r}")
    return book.name


class AnnotationCreate(BaseModel):
    translation_code: str = Field(..., min_length=1, max_length=16)
    book: str = Field(..., min_length=1)
    chapter: int = Field(..., ge=1)
    verse_start: int = Field(..., ge=1)
    verse_end: int = Field(..., ge=1)
    char_start: int = Field(..., ge=0)
    char_end: int = Field(..., ge=0)
    color: HighlightColor
    note: str | None = None

    @model_validator(mode="after")
    def _normalize_and_check(self) -> AnnotationCreate:
        # Normalize the book to its canonical name (raises on unknown).
        object.__setattr__(self, "book", _canonical_book(self.book))
        if self.verse_end < self.verse_start:
            raise ValueError("verse_end must be >= verse_start")
        # char ordering only constrains a single-verse span; across verses the
        # offsets index different verses, so char_end < char_start is valid.
        if self.verse_start == self.verse_end and self.char_end < self.char_start:
            raise ValueError("char_end must be >= char_start within a single verse")
        return self


class AnnotationUpdate(BaseModel):
    """Partial update. Only fields present in the request body are applied
    (detected via `model_fields_set`); note may be set to null to clear it."""

    color: HighlightColor | None = None
    note: str | None = None


class AnnotationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    translation_code: str
    book: str
    chapter: int
    verse_start: int
    verse_end: int
    char_start: int
    char_end: int
    color: HighlightColor
    note: str | None
    created_at: datetime
    updated_at: datetime


class AnnotationEnvelope(BaseModel):
    annotation: AnnotationResponse


class AnnotationListResponse(BaseModel):
    annotations: list[AnnotationResponse]
