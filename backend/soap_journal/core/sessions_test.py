from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.core.passwords import hash_password
from soap_journal.core.sessions import (
    SESSION_TTL,
    cleanup_expired_sessions,
    create_session,
    delete_session,
    extend_session,
    get_session,
)
from soap_journal.db.models.user import User
from soap_journal.db.models.user_session import UserSession


async def _make_user(db: AsyncSession, username: str = "alice") -> User:
    user = User(username=username, password_hash=hash_password("password123"))
    db.add(user)
    await db.flush()
    return user


async def test_create_session_persists_token_and_expiry(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    before = datetime.now(UTC)
    session = await create_session(db_session, user.id)
    after = datetime.now(UTC)

    assert session.token
    assert len(session.token) >= 32
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    # 30-day TTL, with a small tolerance window for the clock advancing between
    # the boundary captures above and create_session's own now().
    assert before + SESSION_TTL - timedelta(seconds=2) <= expires
    assert expires <= after + SESSION_TTL + timedelta(seconds=2)


async def test_get_session_returns_none_for_unknown_token(db_session: AsyncSession) -> None:
    assert await get_session(db_session, "no-such-token") is None


async def test_get_session_returns_none_for_expired_token(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    session = await create_session(db_session, user.id)
    session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()

    assert await get_session(db_session, session.token) is None


async def test_extend_session_pushes_expires_at_forward(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    session = await create_session(db_session, user.id)
    original = session.expires_at
    if original.tzinfo is None:
        original = original.replace(tzinfo=UTC)

    # Move expires_at into the past so extend_session has something to push past.
    session.expires_at = datetime.now(UTC) - timedelta(days=1)
    await db_session.commit()

    await extend_session(db_session, session)
    refreshed = await get_session(db_session, session.token)
    assert refreshed is not None
    new_expires = refreshed.expires_at
    if new_expires.tzinfo is None:
        new_expires = new_expires.replace(tzinfo=UTC)
    assert new_expires > original


async def test_delete_session_removes_row(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    session = await create_session(db_session, user.id)

    await delete_session(db_session, session.token)
    assert await get_session(db_session, session.token) is None
    assert await db_session.get(UserSession, session.id) is None


async def test_cleanup_expired_sessions_only_removes_expired(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session)
    fresh = await create_session(db_session, user.id)
    stale = await create_session(db_session, user.id)

    stale.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()

    await cleanup_expired_sessions(db_session, user.id)

    assert await db_session.get(UserSession, fresh.id) is not None
    assert await db_session.get(UserSession, stale.id) is None
