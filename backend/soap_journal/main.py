from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope

from soap_journal import __version__
from soap_journal.api.admin import router as admin_router
from soap_journal.api.auth import router as auth_router
from soap_journal.api.bible import router as bible_router
from soap_journal.api.entries import router as entries_router
from soap_journal.api.health import router as health_router
from soap_journal.api.tags import router as tags_router
from soap_journal.config import get_settings

ASSET_CACHE_HEADERS = {"Cache-Control": "public, max-age=31536000, immutable"}
INDEX_CACHE_HEADERS = {"Cache-Control": "no-cache"}


class ImmutableAssets(StaticFiles):
    """StaticFiles subclass that stamps Vite-hashed assets with a long
    immutable cache header. Filenames already include a content hash, so
    a year-long max-age is safe."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = ASSET_CACHE_HEADERS["Cache-Control"]
        return response


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    yield


def _mount_frontend(app: FastAPI, dist_dir: Path) -> None:
    """Mount the built frontend bundle. /assets is served with immutable
    cache headers; any other non-API path falls through to index.html for
    SPA client-side routing."""
    assets_dir = dist_dir / "assets"
    index_file = dist_dir / "index.html"

    if assets_dir.is_dir():
        app.mount("/assets", ImmutableAssets(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str, request: Request) -> Response:
        # Belt-and-braces: routers are registered first so /api/* never
        # reaches here, but guard anyway in case of future ordering changes.
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404)
        if not index_file.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(index_file, headers=INDEX_CACHE_HEADERS)


def create_app() -> FastAPI:
    app = FastAPI(
        title="soap-journal",
        version=__version__,
        lifespan=lifespan,
    )
    # API routes MUST be registered before the SPA fallback so the
    # catch-all does not shadow them.
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(bible_router, prefix="/api/v1")
    app.include_router(entries_router, prefix="/api/v1")
    app.include_router(tags_router, prefix="/api/v1")

    settings = get_settings()
    dist_dir = settings.frontend_dist_dir
    if dist_dir is not None and dist_dir.is_dir():
        _mount_frontend(app, dist_dir)

    return app
