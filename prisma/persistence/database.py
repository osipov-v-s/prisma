"""SQLAlchemy engine and session configuration for SQLite or PostgreSQL."""

from collections.abc import Generator
import os
from pathlib import Path
import sys

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


PROJECT_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
DATA_ROOT = Path(os.getenv("PRISMA_DATA_ROOT", PROJECT_ROOT / "data"))
DEFAULT_DATABASE_PATH = DATA_ROOT / "prisma.sqlite"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str | None = None) -> Engine:
    url = database_url or os.getenv("PRISMA_DATABASE_URL", DEFAULT_DATABASE_URL)
    if url.startswith("sqlite"):
        DEFAULT_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine_options = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}
    created_engine = create_engine(url, **engine_options)

    if url.startswith("sqlite"):
        # SQLite disables foreign keys unless each connection enables them.
        @event.listens_for(created_engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return created_engine


engine = make_engine()
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


def get_database_session() -> Generator[Session, None, None]:
    """FastAPI dependency with one transaction boundary per request."""

    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()
