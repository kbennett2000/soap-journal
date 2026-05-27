"""Tests for the FastAPI app factory's static-frontend mount behavior."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Awaitable, Callable

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from soap_journal.config import get_settings
from soap_journal.main import create_app

ClientFactory = Callable[[Path | None], Awaitable[AsyncClient]]


@pytest_asyncio.fixture(loop_scope="session")
async def static_client(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[ClientFactory]:
    """Build a fresh app + AsyncClient per call. FRONTEND_DIST_DIR is set
    (or unset) per build so create_app() picks it up at construction time.

    Lifespan is intentionally not run here — these tests exercise routing,
    not startup side effects. Skipping it avoids tearing the
    session-scoped event loop in fixture cleanup.
    """
    clients: list[AsyncClient] = []

    async def build(frontend_dist_dir: Path | None) -> AsyncClient:
        if frontend_dist_dir is None:
            monkeypatch.delenv("FRONTEND_DIST_DIR", raising=False)
        else:
            monkeypatch.setenv("FRONTEND_DIST_DIR", str(frontend_dist_dir))
        get_settings.cache_clear()
        app: FastAPI = create_app()
        transport = ASGITransport(app=app)
        client = AsyncClient(transport=transport, base_url="http://test")
        clients.append(client)
        return client

    try:
        yield build
    finally:
        for client in clients:
            await client.aclose()
        monkeypatch.delenv("FRONTEND_DIST_DIR", raising=False)
        get_settings.cache_clear()


async def test_dev_mode_root_is_404_without_static_mount(
    static_client: ClientFactory,
) -> None:
    client = await static_client(None)
    response = await client.get("/")
    assert response.status_code == 404


async def test_dev_mode_deep_link_is_404_without_static_mount(
    static_client: ClientFactory,
) -> None:
    client = await static_client(None)
    response = await client.get("/read/BSB/John/3")
    assert response.status_code == 404


async def test_static_mount_serves_index_at_root(
    static_client: ClientFactory, tmp_path: Path
) -> None:
    dist = tmp_path / "frontend-dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>hi</body></html>")

    client = await static_client(dist)
    response = await client.get("/")
    assert response.status_code == 200
    assert "<body>hi</body>" in response.text
    assert response.headers["cache-control"] == "no-cache"


async def test_static_mount_serves_index_for_spa_deep_links(
    static_client: ClientFactory, tmp_path: Path
) -> None:
    dist = tmp_path / "frontend-dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>spa</html>")

    client = await static_client(dist)
    for path in ("/read/BSB/John/3", "/admin", "/entries/123"):
        response = await client.get(path)
        assert response.status_code == 200, path
        assert "spa" in response.text


async def test_api_route_still_works_under_static_mount(
    static_client: ClientFactory, tmp_path: Path
) -> None:
    dist = tmp_path / "frontend-dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>spa</html>")

    client = await static_client(dist)
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


async def test_assets_served_with_immutable_cache_header(
    static_client: ClientFactory, tmp_path: Path
) -> None:
    dist = tmp_path / "frontend-dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>spa</html>")
    (dist / "assets" / "foo.js").write_text("console.log('hi');")

    client = await static_client(dist)
    response = await client.get("/assets/foo.js")
    assert response.status_code == 200
    assert response.text == "console.log('hi');"
    assert (
        response.headers["cache-control"]
        == "public, max-age=31536000, immutable"
    )
