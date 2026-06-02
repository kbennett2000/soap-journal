"""Annotation (highlight) CRUD — user-scoped, separate from entries.

Every route requires `get_current_user` and scopes to that user's id; a user
can only see/modify their own annotations (cross-user access 404s, like
entries). Anchors are FK-free canonical coords + translation_code (ADR-0005), so
nothing here joins to verses/translations.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.api.deps import get_current_user
from soap_journal.core.annotations import (
    apply_update,
    create_annotation,
    get_owned_annotation,
    list_annotations,
)
from soap_journal.core.bible.books import get_book_by_name
from soap_journal.core.errors import ErrorCode, raise_http
from soap_journal.db.models.user import User
from soap_journal.db.session import get_db
from soap_journal.schemas.annotations import (
    AnnotationCreate,
    AnnotationEnvelope,
    AnnotationListResponse,
    AnnotationResponse,
    AnnotationUpdate,
)

router = APIRouter(
    prefix="/annotations",
    tags=["annotations"],
    dependencies=[Depends(get_current_user)],
)


def _envelope(annotation) -> AnnotationEnvelope:  # noqa: ANN001 - ORM row
    return AnnotationEnvelope(annotation=AnnotationResponse.model_validate(annotation))


@router.post("", response_model=AnnotationEnvelope, status_code=status.HTTP_201_CREATED)
async def create(
    body: AnnotationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnnotationEnvelope:
    annotation = await create_annotation(db, user_id=user.id, payload=body)
    await db.commit()
    await db.refresh(annotation)
    return _envelope(annotation)


@router.get("", response_model=AnnotationListResponse)
async def list_for_user(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    translation: Annotated[str | None, Query()] = None,
    book: Annotated[str | None, Query()] = None,
    chapter: Annotated[int | None, Query(ge=1)] = None,
) -> AnnotationListResponse:
    # Normalize the book filter to its canonical name so an alias still matches
    # the stored canonical form.
    canonical_book: str | None = None
    if book is not None:
        resolved = get_book_by_name(book)
        if resolved is None:
            raise_http(
                status.HTTP_400_BAD_REQUEST,
                ErrorCode.INVALID_BOOK,
                f"unknown book: {book!r}",
            )
        canonical_book = resolved.name

    rows = await list_annotations(
        db,
        user_id=user.id,
        translation_code=translation,
        book=canonical_book,
        chapter=chapter,
    )
    return AnnotationListResponse(annotations=[AnnotationResponse.model_validate(r) for r in rows])


@router.patch("/{annotation_id}", response_model=AnnotationEnvelope)
async def update(
    annotation_id: int,
    body: AnnotationUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnnotationEnvelope:
    annotation = await get_owned_annotation(db, user_id=user.id, annotation_id=annotation_id)
    apply_update(annotation, body)
    await db.commit()
    await db.refresh(annotation)
    return _envelope(annotation)


@router.delete("/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    annotation_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    annotation = await get_owned_annotation(db, user_id=user.id, annotation_id=annotation_id)
    await db.delete(annotation)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
