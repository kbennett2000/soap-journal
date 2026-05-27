from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.core.cookies import COOKIE_NAME
from soap_journal.core.errors import ErrorCode, raise_http
from soap_journal.core.sessions import extend_session, get_session
from soap_journal.db.models.user import User
from soap_journal.db.session import get_db


async def _resolve_user(request: Request, db: AsyncSession) -> User | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    session = await get_session(db, token)
    if session is None:
        return None
    user = await db.get(User, session.user_id)
    if user is None:
        return None
    await extend_session(db, session)
    return user


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    user = await _resolve_user(request, db)
    if user is None:
        raise_http(401, ErrorCode.NOT_AUTHENTICATED)
    return user


async def get_current_user_optional(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User | None:
    return await _resolve_user(request, db)


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise_http(403, ErrorCode.ADMIN_REQUIRED)
    return user
