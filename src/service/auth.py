"""Local authentication and administrator user management.

Passwords never leave this module in plain text and bearer tokens live only for
the lifetime of the Python worker.
"""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from src.core.models import Account
from src.db.database import get_db, transaction


_tokens: dict[str, str] = {}
SCRYPT_N = 2**14


class AuthError(ValueError):
    pass


def _hash_password(password: str) -> str:
    if len(password) < 8:
        raise AuthError("Пароль должен содержать не менее 8 символов.")
    salt = os.urandom(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=SCRYPT_N, r=8, p=1, dklen=64
    )
    return f"scrypt${SCRYPT_N}$8$1${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        expected_bytes = bytes.fromhex(expected)
        actual = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r),
            p=int(p), dklen=len(expected_bytes),
        )
        return hmac.compare_digest(actual, expected_bytes)
    except (ValueError, TypeError):
        return False


def login(login_name: str, password: str) -> dict:
    row = _account_row_by_login(login_name)
    if row is None or not row["is_active"] or not _verify_password(password, row["password_hash"]):
        raise AuthError("Неверный логин или пароль.")
    token = secrets.token_urlsafe(32)
    _tokens[token] = row["id"]
    return {"access_token": token, "account": get_account(row["id"]).to_dict()}


def logout(token: str) -> None:
    _tokens.pop(token, None)


def verify_token(token: str, require_admin: bool = False) -> Account:
    account_id = _tokens.get(token)
    account = get_account(account_id) if account_id else None
    if account is None or not account.is_active:
        raise AuthError("Требуется вход в систему.")
    if require_admin and "ADMIN" not in account.roles:
        raise AuthError("Требуются права администратора.")
    return account


def list_users() -> list[dict]:
    with get_db() as connection:
        ids = [row["id"] for row in connection.execute("SELECT id FROM accounts ORDER BY login")]
    return [get_account(account_id).to_dict() for account_id in ids]


def create_user(data: dict) -> dict:
    roles = sorted(set(data.get("roles") or ["USER"]))
    if any(role not in {"USER", "ADMIN"} for role in roles):
        raise AuthError("Допустимые роли: USER и ADMIN.")
    if _account_row_by_login(data["login"]):
        raise AuthError("Пользователь с таким логином уже существует.")
    account_id = str(uuid4())
    with transaction() as connection:
        _insert_account(connection, account_id, data, roles)
    return get_account(account_id).to_dict()


def delete_user(account_id: str, current_account_id: str) -> None:
    if account_id == current_account_id:
        raise AuthError("Нельзя удалить текущую учётную запись.")
    with transaction() as connection:
        cursor = connection.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        if not cursor.rowcount:
            raise AuthError("Пользователь не найден.")


def seed_accounts() -> None:
    if _account_row_by_login("admin") is None:
        create_user({"login": "admin", "password": "admin123",
                     "last_name": "Администратор", "first_name": "ПРИЗМА",
                     "roles": ["ADMIN", "USER"]})
    if _account_row_by_login("user") is None:
        create_user({"login": "user", "password": "user1234",
                     "last_name": "Иванов", "first_name": "Иван",
                     "patronymic": "Иванович", "roles": ["USER"]})


def get_account(account_id: str | None) -> Account | None:
    if not account_id:
        return None
    with get_db() as connection:
        row = connection.execute(
            """SELECT a.id, a.login, a.is_active, p.last_name, p.first_name, p.patronymic
               FROM accounts a JOIN profiles p ON p.account_id = a.id WHERE a.id = ?""",
            (account_id,),
        ).fetchone()
        if row is None:
            return None
        roles = [item["name"] for item in connection.execute(
            """SELECT r.name FROM roles r JOIN account_roles ar ON ar.role_id = r.id
               WHERE ar.account_id = ? ORDER BY r.name""", (account_id,)
        )]
    full_name = " ".join(filter(None, (row["last_name"], row["first_name"], row["patronymic"])))
    return Account(row["id"], row["login"], full_name, roles, bool(row["is_active"]))


def _account_row_by_login(login_name: str):
    expected = login_name.strip().casefold()
    with get_db() as connection:
        return next((row for row in connection.execute("SELECT * FROM accounts")
                     if row["login"].casefold() == expected), None)


def _insert_account(connection, account_id: str, data: dict, roles: list[str]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    connection.execute("INSERT INTO accounts VALUES (?, ?, ?, 1, ?)",
                       (account_id, data["login"].strip(), _hash_password(data["password"]), now))
    connection.execute("INSERT INTO profiles VALUES (?, ?, ?, ?, ?)",
                       (str(uuid4()), account_id, data["last_name"].strip(),
                        data["first_name"].strip(), data.get("patronymic") or None))
    for role_name in roles:
        role = connection.execute("SELECT id FROM roles WHERE name = ?", (role_name,)).fetchone()
        role_id = role["id"] if role else str(uuid4())
        if role is None:
            connection.execute("INSERT INTO roles VALUES (?, ?)", (role_id, role_name))
        connection.execute("INSERT INTO account_roles VALUES (?, ?)", (account_id, role_id))
