"""Pytest configuration and shared fixtures for the soap-journal backend.

Environment variables for `Settings` are set at import time, before any
`soap_journal.*` module loads, so the cached `get_settings()` accessor returns
test values everywhere it's read (including module-level reads).
"""

import os
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

_TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="soap-journal-tests-"))

os.environ["DATA_DIR"] = str(_TEST_DATA_DIR)
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["PORT"] = "8080"
os.environ["BIND_HOST"] = "127.0.0.1"

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from asgi_lifespan import LifespanManager  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool  # noqa: E402

from soap_journal.config import Settings, get_settings  # noqa: E402
from soap_journal.db import models as _models  # noqa: E402, F401  register models on Base.metadata
from soap_journal.db.base import Base  # noqa: E402
from soap_journal.db.session import get_db  # noqa: E402
from soap_journal.main import create_app  # noqa: E402

get_settings.cache_clear()


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session_factory = async_sessionmaker(
            bind=connection, expire_on_commit=False, autoflush=False
        )
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()
                await transaction.rollback()


@pytest.fixture
def app(settings: Settings, db_session: AsyncSession) -> FastAPI:
    application = create_app()

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[get_settings] = lambda: settings
    return application


@pytest_asyncio.fixture(loop_scope="session")
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
