"""In-memory bearer sessions for the local Desktop service."""

from dataclasses import dataclass, field
import secrets
from threading import Lock
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from prisma.persistence.database import get_database_session
from prisma.persistence.models import Account
from prisma.persistence.repositories import AccountRepository


@dataclass
class TokenStore:
    _accounts_by_token: dict[str, str] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def issue(self, account_id: str) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._accounts_by_token[token] = account_id
        return token

    def resolve(self, token: str) -> str | None:
        with self._lock:
            return self._accounts_by_token.get(token)

    def revoke(self, token: str) -> None:
        with self._lock:
            self._accounts_by_token.pop(token, None)


token_store = TokenStore()


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется вход в систему.")
    return authorization.removeprefix("Bearer ").strip()


def current_account(authorization: str | None = Header(default=None),
                    database: Session = Depends(get_database_session)) -> Account:
    account_id = token_store.resolve(_bearer_token(authorization))
    account = AccountRepository(database).get(account_id) if account_id else None
    if account is None or not account.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Сеанс входа недействителен.")
    return account


def account_role_names(account: Account) -> list[str]:
    return sorted(link.role.name for link in account.role_links)


def require_admin(account: Account = Depends(current_account)) -> Account:
    if "ADMIN" not in account_role_names(account):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Требуются права администратора.")
    return account
