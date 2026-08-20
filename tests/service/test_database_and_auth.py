"""Migration compatibility, password authentication, and role checks."""

import sqlite3

import pytest

from src.db.database import set_database_path
from src.db.migrate import migrate, schema_version
from src.service import auth
from src.service.handlers import handle


def test_existing_collection_database_is_adopted_without_data_loss(tmp_path) -> None:
    path = tmp_path / "legacy.sqlite"
    connection = sqlite3.connect(path)
    connection.execute(
        """CREATE TABLE collections (
           id TEXT PRIMARY KEY, name TEXT NOT NULL, width INTEGER NOT NULL,
           depth INTEGER NOT NULL, is_active INTEGER NOT NULL, time_mode TEXT NOT NULL,
           time_limit_ms INTEGER, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
    )
    connection.execute(
        "INSERT INTO collections VALUES ('legacy', 'Старая коллекция', 2, 5, 0, 'no_limit', NULL, 'now', 'now')"
    )
    connection.commit()
    connection.close()

    set_database_path(path)
    migrate()

    check = sqlite3.connect(path)
    assert check.execute("SELECT name FROM collections WHERE id='legacy'").fetchone()[0] == "Старая коллекция"
    check.close()
    assert schema_version() == "002"


def test_login_and_admin_permissions(desktop_db) -> None:
    user = handle("auth.login", {"login": "user", "password": "user1234"})
    with pytest.raises(auth.AuthError, match="права администратора"):
        handle("users.list", {"token": user["access_token"]})

    admin = handle("auth.login", {"login": "admin", "password": "admin123"})
    created = handle("users.create", {
        "token": admin["access_token"],
        "data": {"login": "researcher", "password": "strong-pass",
                 "last_name": "Исследователь", "first_name": "Оксана", "roles": ["USER"]},
    })
    assert created["roles"] == ["USER"]
    handle("users.delete", {"token": admin["access_token"], "account_id": created["id"]})
    assert all(item["id"] != created["id"] for item in auth.list_users())


def test_password_hash_is_not_plain_text(desktop_db) -> None:
    connection = sqlite3.connect(desktop_db)
    stored = connection.execute("SELECT password_hash FROM accounts WHERE login='admin'").fetchone()[0]
    connection.close()
    assert stored != "admin123"
    assert stored.startswith("scrypt$")
