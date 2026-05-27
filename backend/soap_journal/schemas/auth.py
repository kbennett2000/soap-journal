from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

USERNAME_PATTERN = r"^[A-Za-z0-9_-]+$"
USERNAME_MIN = 3
USERNAME_MAX = 32
PASSWORD_MIN = 8

# Reused by /auth/register and the admin user-create / password-reset
# endpoints so validation stays in lockstep across the API.
UsernameStr = Annotated[
    str,
    Field(min_length=USERNAME_MIN, max_length=USERNAME_MAX, pattern=USERNAME_PATTERN),
]
PasswordStr = Annotated[str, Field(min_length=PASSWORD_MIN)]


class RegisterRequest(BaseModel):
    username: UsernameStr
    password: PasswordStr


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
