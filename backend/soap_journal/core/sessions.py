import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.db.models.user_session import UserSession

SESSION_TTL = timedelta(days=30)
SESSION_TOKEN_BYTES = 48


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalize(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


async def create_session(db: AsyncSession, user_id: int) -> UserSession:
    now = _utcnow()
    session = UserSession(
        user_id=user_id,
        token=secrets.token_urlsafe(SESSION_TOKEN_BYTES),
        created_at=now,
        expires_at=now + SESSION_TTL,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, token: str) -> UserSession | None:
    result = await db.execute(select(UserSession).where(UserSession.token == token))
    session = result.scalar_one_or_none()
    if session is None:
        return None
    if _normalize(session.expires_at) <= _utcnow():
        return None
    return session


async def extend_session(db: AsyncSession, session: UserSession) -> None:
    session.expires_at = _utcnow() + SESSION_TTL
    await db.commit()


async def delete_session(db: AsyncSession, token: str) -> None:
    await db.execute(
        delete(UserSession)
        .where(UserSession.token == token)
        .execution_options(synchronize_session="fetch")
    )
    await db.commit()


async def cleanup_expired_sessions(db: AsyncSession, user_id: int) -> None:
    now = _utcnow()
    await db.execute(
        delete(UserSession)
        .where(
            UserSession.user_id == user_id,
            UserSession.expires_at <= now,
        )
        .execution_options(synchronize_session="fetch")
    )
    await db.commit()


async def delete_user_sessions(db: AsyncSession, user_id: int) -> None:
    """Invalidate every active session for a user. Used by admin password
    reset and as a pre-step to a user delete."""
    await db.execute(
        delete(UserSession)
        .where(UserSession.user_id == user_id)
        .execution_options(synchronize_session="fetch")
    )
    await db.commit()
