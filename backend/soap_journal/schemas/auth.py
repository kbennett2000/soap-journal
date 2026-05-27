import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
USERNAME_MIN = 3
USERNAME_MAX = 32
PASSWORD_MIN = 8


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=USERNAME_MIN, max_length=USERNAME_MAX)
    password: str = Field(..., min_length=PASSWORD_MIN)

    @field_validator("username")
    @classmethod
    def _username_charset(cls, value: str) -> str:
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError(
                "username must contain only ASCII letters, digits, underscore, or hyphen"
            )
        return value


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    is_admin: bool
    created_at: datetime


class AuthEnvelope(BaseModel):
    user: UserResponse
