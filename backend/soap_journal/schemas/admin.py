from pydantic import BaseModel, ConfigDict

from soap_journal.schemas.auth import PasswordStr, UserResponse, UsernameStr


class UserCreateRequest(BaseModel):
    username: UsernameStr
    password: PasswordStr
    is_admin: bool = False


class ResetPasswordRequest(BaseModel):
    new_password: PasswordStr


class UserListResponse(BaseModel):
    users: list[UserResponse]


class SettingsView(BaseModel):
    # `extra="forbid"` rejects unknown keys in PUT bodies. Adding a new
    # setting in v2 means: bump a migration to seed the row + add a field
    # here. No stringly-typed key endpoints to babysit.
    model_config = ConfigDict(extra="forbid")

    open_registration: bool


class SettingsEnvelope(BaseModel):
    settings: SettingsView
