from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.api.deps import get_current_user
from soap_journal.core.cookies import (
    COOKIE_NAME,
    clear_session_cookie,
    set_session_cookie,
)
from soap_journal.core.errors import ErrorCode, raise_http
from soap_journal.core.passwords import hash_password, verify_password
from soap_journal.core.sessions import (
    cleanup_expired_sessions,
    create_session,
    delete_session,
)
from soap_journal.core.settings_store import is_open_registration
from soap_journal.db.models.user import User
from soap_journal.db.session import get_db
from soap_journal.schemas.auth import (
    AuthEnvelope,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _count_users(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(User))
    return int(result.scalar_one())


async def _get_user_by_username(db: AsyncSession, username_lower: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username_lower))
    return result.scalar_one_or_none()


@router.post(
    "/register",
    response_model=AuthEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthEnvelope:
    username_lower = body.username.lower()

    is_first_user = (await _count_users(db)) == 0
    if not is_first_user and not await is_open_registration(db):
        raise_http(status.HTTP_403_FORBIDDEN, ErrorCode.REGISTRATION_CLOSED)

    if await _get_user_by_username(db, username_lower) is not None:
        raise_http(status.HTTP_409_CONFLICT, ErrorCode.USERNAME_TAKEN)

    user = User(
        username=username_lower,
        password_hash=hash_password(body.password),
        is_admin=is_first_user,
    )
    db.add(user)
    await db.flush()

    session = await create_session(db, user.id)
    set_session_cookie(response, session.token)

    return AuthEnvelope(user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthEnvelope)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthEnvelope:
    username_lower = body.username.lower()
    user = await _get_user_by_username(db, username_lower)
    # Identical response shape whether the user exists or the password is wrong.
    if user is None or not verify_password(body.password, user.password_hash):
        raise_http(status.HTTP_401_UNAUTHORIZED, ErrorCode.INVALID_CREDENTIALS)

    await cleanup_expired_sessions(db, user.id)
    session = await create_session(db, user.id)
    set_session_cookie(response, session.token)

    return AuthEnvelope(user=UserResponse.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> None:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        await delete_session(db, token)
    clear_session_cookie(response)


@router.get("/me", response_model=AuthEnvelope)
async def me(user: User = Depends(get_current_user)) -> AuthEnvelope:
    return AuthEnvelope(user=UserResponse.model_validate(user))
