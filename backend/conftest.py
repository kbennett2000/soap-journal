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


_BSB_SOURCE = Path(__file__).parent.parent / "bible-sources" / "bsb" / "bsb.txt"


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def bsb_loaded(engine: AsyncEngine) -> AsyncIterator[None]:
    """Load the bundled BSB into the test DB once for the whole session.

    Bible tests opt in by depending on this fixture. The load runs against
    a dedicated committed connection so the data persists across per-test
    transactions that roll back. Using the real BSB (not a synthetic
    mini-translation) keeps the tests honest about chapter counts,
    omitted-verse handling, and book-boundary navigation.
    """
    if not _BSB_SOURCE.exists():
        pytest.skip("BSB source not bundled; skipping BSB-dependent tests")

    from soap_journal.cli.load_translation import load_canonical_translation  # noqa: E402
    from soap_journal.parsers.bsb import parse_bsb_source  # noqa: E402

    text = _BSB_SOURCE.read_text(encoding="utf-8")
    translation, _renames = parse_bsb_source(text)

    async with engine.connect() as connection:
        session_factory = async_sessionmaker(
            bind=connection, expire_on_commit=False, autoflush=False
        )
        async with session_factory() as session:
            await load_canonical_translation(session, translation)
            await session.commit()
    yield


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
