"""Canonical JSON schema for Bible text.

Every parser targets this format. The loader CLI consumes it. The reader
(future slice) reads only canonical-format data from the DB. Adding a new
translation = write a parser whose output validates against this schema.

This is the v1 schema freeze (per CLAUDE.md). Breaking changes here ripple
through every parser and the loader; additions are safe as long as defaults
keep old canonical JSON files valid.

Notes (formerly "footnotes") may optionally carry a type, a character anchor
into the verse text, a render ordinal, and cross-references to other verses.
These fields exist to absorb rich translator's-note translations (e.g. the
NET Bible). They are all optional/defaulted: a translation that emits plain
untyped footnotes (all 13 bundled public-domain translations) leaves them
unset and validates unchanged. See docs/adr/0001-unified-bible-notes-data-model.md.

Out of scope for v1 (deliberately omitted to keep the format small):
- Multi-translation parallel text.
- Full-text search indexing over verses/notes.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from soap_journal.core.bible.books import ALL_BOOKS, get_book_by_name

NoteType = Literal["tn", "sn", "tc", "map"]
"""Typed translator-note categories: translator, study, text-critical, map."""


def _strict() -> ConfigDict:
    """Reject unknown fields; ensure the schema stays the single source of truth."""
    return ConfigDict(extra="forbid")


class CanonicalVerse(BaseModel):
    model_config = _strict()

    number: int = Field(..., ge=1, description="Verse number within the chapter, 1-based.")
    text: str = Field(..., min_length=1, description="Verse text. Whitespace-trimmed, non-empty.")
    is_red_letter: bool = Field(
        default=False,
        description="True if this verse is words-of-Christ (red-letter). Defaults to false.",
    )


class CanonicalHeading(BaseModel):
    model_config = _strict()

    before_verse: int = Field(
        ...,
        ge=1,
        description=(
            "Verse number this heading appears before (inclusive). Must "
            "reference an existing verse in the chapter."
        ),
    )
    text: str = Field(..., min_length=1, description="Heading text. Whitespace-trimmed.")


class CanonicalCrossRef(BaseModel):
    """A cross-reference from a note to a verse (or verse range) elsewhere.

    The target is identified by canonical book order (1..66), chapter, and a
    verse range — not a resolved verse row. Targets may span books absent from
    the current chapter and may be produced by best-effort extraction, so the
    loader resolves only the book (to this translation's row); the chapter and
    verse numbers are resolved to verses at read time.
    """

    model_config = _strict()

    to_book_order_index: int = Field(
        ...,
        ge=1,
        le=66,
        description="Canonical book order of the target (1..66), matching ALL_BOOKS.",
    )
    to_chapter: int = Field(..., ge=1, description="Target chapter number, 1-based.")
    to_verse_start: int = Field(..., ge=1, description="First target verse number, 1-based.")
    to_verse_end: int | None = Field(
        default=None,
        ge=1,
        description="Last target verse number for a range; None for a single verse.",
    )

    @model_validator(mode="after")
    def _end_after_start(self) -> CanonicalCrossRef:
        if self.to_verse_end is not None and self.to_verse_end < self.to_verse_start:
            raise ValueError(
                f"cross-ref to_verse_end={self.to_verse_end} is before "
                f"to_verse_start={self.to_verse_start}"
            )
        return self


class CanonicalFootnote(BaseModel):
    """A note attached to a verse. Plain (untyped) by default; optionally typed,
    character-anchored, ordered, and carrying cross-references."""

    model_config = _strict()

    verse_number: int = Field(
        ...,
        ge=1,
        description=(
            "Verse number this footnote belongs to. Must reference an "
            "existing verse in the chapter."
        ),
    )
    text: str = Field(..., min_length=1, description="Footnote text. Whitespace-trimmed.")
    note_type: NoteType | None = Field(
        default=None,
        description="Typed-note category (tn/sn/tc/map). None for a plain footnote.",
    )
    char_offset: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Character offset into the verse text where the note anchors. None "
            "when the note is not anchored. Validated against verse length at the "
            "chapter level."
        ),
    )
    marker: int | None = Field(
        default=None,
        description="Source-provenance marker ordinal (e.g. per-page). Not semantic.",
    )
    ordinal: int | None = Field(
        default=None,
        ge=0,
        description="Stable render order of this note within its verse, 0-based.",
    )
    cross_refs: list[CanonicalCrossRef] = Field(
        default_factory=list,
        description="Cross-references contained in this note. Empty when there are none.",
    )


class CanonicalChapter(BaseModel):
    model_config = _strict()

    number: int = Field(..., ge=1, description="Chapter number within the book, 1-based.")
    verses: list[CanonicalVerse] = Field(
        ...,
        min_length=1,
        description="Verses in this chapter, ordered 1..N with no gaps or duplicates.",
    )
    headings: list[CanonicalHeading] = Field(
        default_factory=list,
        description="Section headings interleaved with verses. Empty when the source has none.",
    )
    footnotes: list[CanonicalFootnote] = Field(
        default_factory=list,
        description="Footnotes attached to verses. Empty when the source has none.",
    )

    @model_validator(mode="after")
    def _verses_are_1_to_n(self) -> CanonicalChapter:
        numbers = [v.number for v in self.verses]
        expected = list(range(1, len(numbers) + 1))
        if numbers != expected:
            raise ValueError(
                f"chapter {self.number} verses must be numbered 1..N "
                f"with no gaps or duplicates, got {numbers}"
            )
        return self

    @model_validator(mode="after")
    def _headings_reference_existing_verses(self) -> CanonicalChapter:
        verse_numbers = {v.number for v in self.verses}
        for heading in self.headings:
            if heading.before_verse not in verse_numbers:
                raise ValueError(
                    f"chapter {self.number} heading before_verse={heading.before_verse} "
                    f"does not match any verse"
                )
        return self

    @model_validator(mode="after")
    def _footnotes_reference_existing_verses(self) -> CanonicalChapter:
        verse_numbers = {v.number for v in self.verses}
        for footnote in self.footnotes:
            if footnote.verse_number not in verse_numbers:
                raise ValueError(
                    f"chapter {self.number} footnote verse_number={footnote.verse_number} "
                    f"does not match any verse"
                )
        return self

    @model_validator(mode="after")
    def _footnote_char_offsets_within_verse(self) -> CanonicalChapter:
        verse_text_len = {v.number: len(v.text) for v in self.verses}
        for footnote in self.footnotes:
            if footnote.char_offset is None:
                continue
            length = verse_text_len.get(footnote.verse_number)
            # A missing verse is already reported by the reference validator.
            if length is not None and footnote.char_offset > length:
                raise ValueError(
                    f"chapter {self.number} footnote on verse "
                    f"{footnote.verse_number} has char_offset={footnote.char_offset} "
                    f"beyond verse length {length}"
                )
        return self


class CanonicalBook(BaseModel):
    model_config = _strict()

    name: str = Field(
        ...,
        description="Canonical book name (must match soap_journal.core.bible.books.ALL_BOOKS).",
    )
    abbreviation: str = Field(..., description="Canonical short form for the book.")
    order_index: int = Field(..., ge=1, le=66, description="1..66 canonical order.")
    chapters: list[CanonicalChapter] = Field(
        ...,
        min_length=1,
        description="Chapters in this book, ordered 1..N with no gaps or duplicates.",
    )

    @model_validator(mode="after")
    def _name_is_canonical(self) -> CanonicalBook:
        canon = get_book_by_name(self.name)
        if canon is None or canon.name != self.name:
            raise ValueError(
                f"book name {self.name!r} is not the canonical form; "
                f"use the exact name from ALL_BOOKS"
            )
        if canon.order_index != self.order_index:
            raise ValueError(
                f"book {self.name!r} expects order_index={canon.order_index}, "
                f"got {self.order_index}"
            )
        if canon.abbreviation != self.abbreviation:
            raise ValueError(
                f"book {self.name!r} expects abbreviation={canon.abbreviation!r}, "
                f"got {self.abbreviation!r}"
            )
        return self

    @model_validator(mode="after")
    def _chapters_are_1_to_n(self) -> CanonicalBook:
        numbers = [c.number for c in self.chapters]
        expected = list(range(1, len(numbers) + 1))
        if numbers != expected:
            raise ValueError(
                f"book {self.name!r} chapters must be numbered 1..N "
                f"with no gaps or duplicates, got {numbers}"
            )
        return self


class CanonicalTranslation(BaseModel):
    model_config = _strict()

    code: str = Field(..., min_length=1, description="Short uppercase code, e.g. 'BSB'.")
    name: str = Field(..., min_length=1, description="Full translation name.")
    language: str = Field(
        ...,
        min_length=2,
        max_length=8,
        description=(
            "ISO 639-1 language code (e.g. 'en'). Long enough for IETF "
            "tags like 'en-US' if a parser ever needs it."
        ),
    )
    copyright: str = Field(
        ...,
        min_length=1,
        description="Attribution / license text for the translation.",
    )
    books: list[CanonicalBook] = Field(
        ...,
        description="All 66 books in canonical order. Must match ALL_BOOKS exactly.",
    )

    @model_validator(mode="after")
    def _books_match_canon(self) -> CanonicalTranslation:
        expected = [(b.order_index, b.name) for b in ALL_BOOKS]
        actual = [(b.order_index, b.name) for b in self.books]
        if actual != expected:
            # Pinpoint the first mismatch so the parser error is actionable.
            for i, (want, got) in enumerate(zip(expected, actual, strict=False)):
                if want != got:
                    raise ValueError(
                        f"books[{i}] expected (order_index={want[0]}, name={want[1]!r}), "
                        f"got (order_index={got[0]}, name={got[1]!r})"
                    )
            if len(actual) != len(expected):
                raise ValueError(
                    f"translation must have exactly {len(expected)} books, got {len(actual)}"
                )
        return self
