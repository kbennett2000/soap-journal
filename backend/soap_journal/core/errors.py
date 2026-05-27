from enum import StrEnum
from typing import NoReturn

from fastapi import HTTPException


class ErrorCode(StrEnum):
    USERNAME_TAKEN = "USERNAME_TAKEN"
    REGISTRATION_CLOSED = "REGISTRATION_CLOSED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
    ADMIN_REQUIRED = "ADMIN_REQUIRED"


def raise_http(status: int, code: ErrorCode, message: str | None = None) -> NoReturn:
    raise HTTPException(
        status_code=status,
        detail={"code": code.value, "message": message or code.value},
    )
