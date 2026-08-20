"""Minimal SQLite wrapper shared by all Desktop services."""

from collections.abc import Generator, Iterable
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(os.getenv("PRISMA_DATA_ROOT", PROJECT_ROOT / "data"))
_database_path = DATA_ROOT / "prisma.sqlite"


def set_database_path(path: Path) -> None:
    """Point services to an isolated database, primarily for tests."""

    global _database_path
    _database_path = Path(path)


def database_path() -> Path:
    return _database_path


def _connect() -> sqlite3.Connection:
    _database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(_database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Open a read-oriented connection and always close it."""

    connection = _connect()
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def transaction() -> Generator[sqlite3.Connection, None, None]:
    """Commit all writes together or roll them back on an error."""

    connection = _connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def query_one(sql: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
    with get_db() as connection:
        return connection.execute(sql, tuple(params)).fetchone()


def query_all(sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    with get_db() as connection:
        return list(connection.execute(sql, tuple(params)).fetchall())


def execute(sql: str, params: Iterable[Any] = ()) -> int:
    with transaction() as connection:
        cursor = connection.execute(sql, tuple(params))
        return cursor.lastrowid


def execute_many(sql: str, params_list: Iterable[Iterable[Any]]) -> None:
    with transaction() as connection:
        connection.executemany(sql, params_list)
