"""Pydantic request/response schemas for SOAP journal entries + tags."""

from __future__ import annotations

import unicodedata
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TAG_MAX_LEN = 50


class EntryTagSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class _EntryWritable(BaseModel):
    """Fields shared by create and update payloads.

    Both endpoints share this shape — PUT is replace-not-patch, so they
    are intentionally the same model.
    """

    title: str | None = None
    entry_date: date | None = None
    scripture_ref: str = Field(..., min_length=1, max_length=200)
    translation_code: str | None = None
    observation: str = ""
    application: str = ""
    prayer: str = ""
    tags: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def _trim_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        if len(trimmed) > 200:
            raise ValueError("title exceeds 200 characters")
        return trimmed

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for tag in value:
            if not isinstance(tag, str):
                raise ValueError("tags must be strings")
            stripped = tag.strip()
            if not stripped:
                raise ValueError("tag cannot be empty after trim")
            if len(stripped) > TAG_MAX_LEN:
                raise ValueError(f"tag exceeds {TAG_MAX_LEN} characters")
            if any(unicodedata.category(c).startswith("C") for c in stripped):
                raise ValueError("tag contains control characters")
            cleaned.append(stripped)
        return cleaned


class EntryCreateRequest(_EntryWritable):
    pass


class EntryUpdateRequest(_EntryWritable):
    pass


class EntryResponse(BaseModel):
    id: int
    title: str | None
    display_title: str
    entry_date: date
    scripture_ref: str
    translation_code: str
    scripture_text: str
    observation: str
    application: str
    prayer: str
    tags: list[EntryTagSummary]
    created_at: datetime
    updated_at: datetime


class EntryEnvelope(BaseModel):
    entry: EntryResponse


class AppliedFilters(BaseModel):
    q: str | None = None
    book: str | None = None
    tag: str | None = None
    from_date: date | None = None
    to_date: date | None = None


class EntryListResponse(BaseModel):
    entries: list[EntryResponse]
    total: int
    limit: int
    offset: int
    applied_filters: AppliedFilters


class CalendarDay(BaseModel):
    entry_date: date
    count: int


class CalendarResponse(BaseModel):
    year: int
    month: int
    days: list[CalendarDay]
    total: int


class OnThisDayResponse(BaseModel):
    target_date: date
    entries: list[EntryResponse]


# ---- tags ------------------------------------------------------------------


class TagSummary(BaseModel):
    id: int
    name: str
    entry_count: int


class TagListResponse(BaseModel):
    tags: list[TagSummary]


class TagAutocompleteResponse(BaseModel):
    tags: list[TagSummary]


# ---- list query ------------------------------------------------------------

EntryListOrder = Literal["newest", "oldest"]
