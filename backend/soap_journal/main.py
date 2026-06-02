import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope

from soap_journal import __version__
from soap_journal.api.admin import router as admin_router
from soap_journal.api.annotations import router as annotations_router
from soap_journal.api.auth import router as auth_router
from soap_journal.api.bible import router as bible_router
from soap_journal.api.entries import router as entries_router
from soap_journal.api.health import router as health_router
from soap_journal.api.tags import router as tags_router
from soap_journal.config import SECRET_KEY_FILENAME, get_settings

ASSET_CACHE_HEADERS = {"Cache-Control": "public, max-age=31536000, immutable"}
INDEX_CACHE_HEADERS = {"Cache-Control": "no-cache"}

logger = logging.getLogger("soap_journal")


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

    logger.info("soap-journal %s starting", __version__)
    logger.info("data_dir = %s", settings.data_dir)
    key_file = settings.data_dir / SECRET_KEY_FILENAME
    if key_file.is_file():
        logger.info("secret key loaded from %s", key_file)
    else:
        logger.info("secret key loaded from environment")
    dist_dir = settings.frontend_dist_dir
    if dist_dir is not None and dist_dir.is_dir():
        logger.info("frontend dist mounted from %s", dist_dir)
    else:
        logger.info("frontend dist not mounted (dev mode)")

    yield


def _resolve_top_level_static(dist_dir: Path, name: str) -> Path | None:
    """Return the path to a top-level static file under dist_dir, or None.

    Single-segment names only; refuses anything that would resolve outside
    the dist directory (`..` traversal, symlinks). Kept synchronous on
    purpose — see callsite in `_mount_frontend.spa_fallback`.
    """
    candidate = dist_dir / name
    if not candidate.is_file():
        return None
    resolved = candidate.resolve()
    if not resolved.is_relative_to(dist_dir.resolve()):
        return None
    return resolved


def _mount_frontend(app: FastAPI, dist_dir: Path) -> None:
    """Mount the built frontend bundle. /assets is served with immutable
    cache headers; specific top-level files (favicon, robots) are served
    from disk; everything else falls through to index.html for SPA
    client-side routing."""
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
        # Top-level static files Vite drops into dist/ root (favicon.svg,
        # robots.txt, etc.). Restricted to files that actually exist so the
        # SPA fallback still handles unknown routes.
        if full_path and "/" not in full_path:
            resolved = _resolve_top_level_static(dist_dir, full_path)
            if resolved is not None:
                return FileResponse(resolved)
        if not index_file.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(index_file, headers=INDEX_CACHE_HEADERS)


def create_app() -> FastAPI:
    # Uvicorn configures its own `uvicorn` loggers but doesn't touch the
    # root logger, so `soap_journal.*` messages get dropped by default.
    # Wire up a handler iff nothing else has — tests and embedders can
    # set their own config first and we won't clobber it.
    if not logging.getLogger("soap_journal").handlers and not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

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
    app.include_router(annotations_router, prefix="/api/v1")

    settings = get_settings()
    dist_dir = settings.frontend_dist_dir
    if dist_dir is not None and dist_dir.is_dir():
        _mount_frontend(app, dist_dir)

    return app
