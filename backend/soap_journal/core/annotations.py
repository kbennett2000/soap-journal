"""Data operations for annotations (highlights).

Thin, user-scoped helpers behind the annotations router — the data-layer
counterpart to `core/entries.py`. Callers (the router) own the transaction
boundary (commit/rollback).
"""

from __future__ import annotations

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.core.errors import ErrorCode, raise_http
from soap_journal.db.models.annotation import Annotation
from soap_journal.schemas.annotations import AnnotationCreate, AnnotationUpdate


async def create_annotation(
    db: AsyncSession, *, user_id: int, payload: AnnotationCreate
) -> Annotation:
    annotation = Annotation(
        user_id=user_id,
        translation_code=payload.translation_code,
        book=payload.book,  # already normalized to the canonical name by the schema
        chapter=payload.chapter,
        verse_start=payload.verse_start,
        verse_end=payload.verse_end,
        char_start=payload.char_start,
        char_end=payload.char_end,
        color=payload.color,
        note=payload.note,
    )
    db.add(annotation)
    await db.flush()
    return annotation


async def get_owned_annotation(db: AsyncSession, *, user_id: int, annotation_id: int) -> Annotation:
    """Return the annotation iff it belongs to this user, else 404.

    Cross-user access returns 404 (not 403) so the API never reveals that
    another user's annotation exists — same convention as entries.
    """
    annotation = await db.get(Annotation, annotation_id)
    if annotation is None or annotation.user_id != user_id:
        raise_http(
            status.HTTP_404_NOT_FOUND,
            ErrorCode.ANNOTATION_NOT_FOUND,
            f"annotation {annotation_id} not found",
        )
    return annotation


async def list_annotations(
    db: AsyncSession,
    *,
    user_id: int,
    translation_code: str | None = None,
    book: str | None = None,
    chapter: int | None = None,
) -> list[Annotation]:
    """List a user's annotations, optionally filtered for the reader's
    per-chapter fetch. Ordered by canonical position for stable rendering."""
    stmt = select(Annotation).where(Annotation.user_id == user_id)
    if translation_code is not None:
        stmt = stmt.where(Annotation.translation_code == translation_code)
    if book is not None:
        stmt = stmt.where(Annotation.book == book)
    if chapter is not None:
        stmt = stmt.where(Annotation.chapter == chapter)
    stmt = stmt.order_by(
        Annotation.book.asc(),
        Annotation.chapter.asc(),
        Annotation.verse_start.asc(),
        Annotation.char_start.asc(),
        Annotation.id.asc(),
    )
    return list((await db.execute(stmt)).scalars().all())


def apply_update(annotation: Annotation, payload: AnnotationUpdate) -> None:
    """Apply a partial update in place. Only fields explicitly present in the
    request body are touched (so PATCH leaves omitted fields alone); `note` may
    be set to null to clear it."""
    fields = payload.model_fields_set
    if "color" in fields and payload.color is not None:
        annotation.color = payload.color
    if "note" in fields:
        annotation.note = payload.note
