"""FastAPI entry point for the local PRISMA application service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from prisma.persistence.database import SessionFactory
from prisma.persistence.migration import upgrade_database

from .config import API_PREFIX, COLLECTION_STORAGE_ROOT, SERVICE_NAME, SERVICE_VERSION
from .routes import analysis, auth, collections, experiments, system, users
from .seed import seed_database
from .storage import prepare_storage


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Migrations and seed are idempotent, so Desktop can safely start the service.
    prepare_storage()
    upgrade_database()
    with SessionFactory() as session:
        seed_database(session)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=SERVICE_NAME,
        version=SERVICE_VERSION,
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(system.router, prefix=API_PREFIX)
    app.include_router(auth.router, prefix=API_PREFIX)
    app.include_router(analysis.router, prefix=API_PREFIX)
    app.include_router(collections.router, prefix=API_PREFIX)
    app.include_router(users.router, prefix=API_PREFIX)
    app.include_router(experiments.router, prefix=API_PREFIX)
    app.mount(
        "/media",
        StaticFiles(directory=COLLECTION_STORAGE_ROOT, check_dir=False),
        name="media",
    )
    return app


app = create_app()
