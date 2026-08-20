"""Isolated sqlite3 database shared by direct service tests."""

from pathlib import Path

import pytest

from src.db.database import set_database_path
from src.service.handlers import initialize


@pytest.fixture()
def desktop_db(tmp_path: Path) -> Path:
    path = tmp_path / "prisma.sqlite"
    set_database_path(path)
    initialize()
    return path
