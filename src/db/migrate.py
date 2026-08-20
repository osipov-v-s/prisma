"""Apply ordered SQL files and adopt databases created by the former Alembic layer."""

from pathlib import Path
import sqlite3

from .database import transaction


MIGRATIONS_ROOT = Path(__file__).with_name("migrations")


def migrate() -> None:
    """Apply every missing migration without altering existing application rows."""

    with transaction() as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY)"
        )
        applied = {
            row["version"]
            for row in connection.execute("SELECT version FROM schema_migrations")
        }
        for path in sorted(MIGRATIONS_ROOT.glob("[0-9][0-9][0-9]_*.sql")):
            version = path.name.split("_", 1)[0]
            if version in applied:
                continue
            connection.executescript(path.read_text(encoding="utf-8"))
            connection.execute(
                "INSERT INTO schema_migrations(version) VALUES (?)", (version,)
            )


def schema_version() -> str | None:
    with transaction() as connection:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        if not table:
            return None
        row = connection.execute("SELECT MAX(version) AS version FROM schema_migrations").fetchone()
        return row["version"]
