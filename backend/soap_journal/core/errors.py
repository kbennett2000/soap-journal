from enum import StrEnum
from typing import NoReturn

from fastapi import HTTPException


class ErrorCode(StrEnum):
    USERNAME_TAKEN = "USERNAME_TAKEN"
    REGISTRATION_CLOSED = "REGISTRATION_CLOSED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
    ADMIN_REQUIRED = "ADMIN_REQUIRED"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    LAST_ADMIN = "LAST_ADMIN"
    INVALID_REFERENCE = "INVALID_REFERENCE"
    TRANSLATION_NOT_FOUND = "TRANSLATION_NOT_FOUND"
    BOOK_NOT_FOUND = "BOOK_NOT_FOUND"
    CHAPTER_NOT_FOUND = "CHAPTER_NOT_FOUND"
    REFERENCE_OUT_OF_RANGE = "REFERENCE_OUT_OF_RANGE"
    ENTRY_NOT_FOUND = "ENTRY_NOT_FOUND"
    ANNOTATION_NOT_FOUND = "ANNOTATION_NOT_FOUND"
    INVALID_BOOK = "INVALID_BOOK"
    INVALID_DATE_RANGE = "INVALID_DATE_RANGE"


def raise_http(status: int, code: ErrorCode, message: str | None = None) -> NoReturn:
    raise HTTPException(
        status_code=status,
        detail={"code": code.value, "message": message or code.value},
    )
