from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from soap_journal import __version__
from soap_journal.api.health import router as health_router
from soap_journal.config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="soap-journal",
        version=__version__,
        lifespan=lifespan,
    )
    app.include_router(health_router, prefix="/api/v1")
    return app
