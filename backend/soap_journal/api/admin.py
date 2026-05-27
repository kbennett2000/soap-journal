from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.api.deps import require_admin
from soap_journal.core.errors import ErrorCode, raise_http
from soap_journal.core.passwords import hash_password
from soap_journal.core.sessions import delete_user_sessions
from soap_journal.core.settings_store import (
    is_open_registration,
    set_open_registration,
)
from soap_journal.db.models.user import User
from soap_journal.db.session import get_db
from soap_journal.schemas.admin import (
    ResetPasswordRequest,
    SettingsEnvelope,
    SettingsView,
    UserCreateRequest,
    UserListResponse,
)
from soap_journal.schemas.auth import AuthEnvelope, UserResponse

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


async def _get_user_or_404(db: AsyncSession, user_id: int) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise_http(status.HTTP_404_NOT_FOUND, ErrorCode.USER_NOT_FOUND)
    return user


async def _count_admins(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count()).select_from(User).where(User.is_admin.is_(True))
    )
    return int(result.scalar_one())


async def _username_taken(db: AsyncSession, username_lower: str) -> bool:
    result = await db.execute(select(User.id).where(User.username == username_lower))
    return result.scalar_one_or_none() is not None


# ---- users -----------------------------------------------------------------


@router.get("/users", response_model=UserListResponse)
async def list_users(db: AsyncSession = Depends(get_db)) -> UserListResponse:
    result = await db.execute(select(User).order_by(User.created_at.asc(), User.id.asc()))
    users = result.scalars().all()
    return UserListResponse(users=[UserResponse.model_validate(u) for u in users])


@router.post(
    "/users",
    response_model=AuthEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    body: UserCreateRequest, db: AsyncSession = Depends(get_db)
) -> AuthEnvelope:
    username_lower = body.username.lower()
    if await _username_taken(db, username_lower):
        raise_http(status.HTTP_409_CONFLICT, ErrorCode.USERNAME_TAKEN)

    user = User(
        username=username_lower,
        password_hash=hash_password(body.password),
        is_admin=body.is_admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return AuthEnvelope(user=UserResponse.model_validate(user))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int, db: AsyncSession = Depends(get_db)
) -> Response:
    user = await _get_user_or_404(db, user_id)

    if user.is_admin and await _count_admins(db) <= 1:
        raise_http(status.HTTP_409_CONFLICT, ErrorCode.LAST_ADMIN)

    # FK enforcement isn't enabled on SQLite by default, so drop the user's
    # sessions explicitly before deleting the user row.
    await delete_user_sessions(db, user.id)
    await db.delete(user)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/users/{user_id}/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reset_password(
    user_id: int,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> Response:
    user = await _get_user_or_404(db, user_id)
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    # Force re-login on every device the user is signed in on.
    await delete_user_sessions(db, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/users/{user_id}/promote", response_model=AuthEnvelope)
async def promote_user(
    user_id: int, db: AsyncSession = Depends(get_db)
) -> AuthEnvelope:
    user = await _get_user_or_404(db, user_id)
    if not user.is_admin:
        user.is_admin = True
        await db.commit()
        await db.refresh(user)
    return AuthEnvelope(user=UserResponse.model_validate(user))


@router.post("/users/{user_id}/demote", response_model=AuthEnvelope)
async def demote_user(
    user_id: int, db: AsyncSession = Depends(get_db)
) -> AuthEnvelope:
    user = await _get_user_or_404(db, user_id)

    if user.is_admin:
        if await _count_admins(db) <= 1:
            raise_http(status.HTTP_409_CONFLICT, ErrorCode.LAST_ADMIN)
        user.is_admin = False
        await db.commit()
        await db.refresh(user)

    return AuthEnvelope(user=UserResponse.model_validate(user))


# ---- settings --------------------------------------------------------------


@router.get("/settings", response_model=SettingsEnvelope)
async def get_settings_view(
    db: AsyncSession = Depends(get_db),
) -> SettingsEnvelope:
    view = SettingsView(open_registration=await is_open_registration(db))
    return SettingsEnvelope(settings=view)


@router.put("/settings", response_model=SettingsEnvelope)
async def update_settings(
    body: SettingsView, db: AsyncSession = Depends(get_db)
) -> SettingsEnvelope:
    await set_open_registration(db, body.open_registration)
    return SettingsEnvelope(settings=body)
