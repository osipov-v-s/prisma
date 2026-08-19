"""Account persistence kept separate from authentication and HTTP."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Account, AccountRole, Profile, Role


class AccountRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _relations():
        return (
            selectinload(Account.profile),
            selectinload(Account.role_links).selectinload(AccountRole.role),
        )

    def list(self) -> list[Account]:
        return list(self.session.scalars(
            select(Account).options(*self._relations()).order_by(Account.login)
        ).all())

    def get(self, account_id: str) -> Account | None:
        return self.session.scalar(
            select(Account).where(Account.id == account_id).options(*self._relations())
        )

    def find_by_login(self, login: str) -> Account | None:
        expected = login.strip().casefold()
        return next(
            (account for account in self.list() if account.login.casefold() == expected),
            None,
        )

    def get_or_create_role(self, name: str) -> Role:
        role = self.session.scalar(select(Role).where(Role.name == name))
        if role is None:
            role = Role(name=name)
            self.session.add(role)
            self.session.flush()
        return role

    def create(self, *, login: str, password_hash: str, last_name: str,
               first_name: str, patronymic: str | None,
               roles: tuple[str, ...]) -> Account:
        account = Account(login=login.strip(), password_hash=password_hash)
        account.profile = Profile(
            last_name=last_name.strip(), first_name=first_name.strip(),
            patronymic=patronymic.strip() if patronymic else None,
        )
        self.session.add(account)
        self.session.flush()
        resolved_roles = [self.get_or_create_role(role_name) for role_name in roles]
        links = [AccountRole(account=account, role=role) for role in resolved_roles]
        self.session.add_all(links)
        self.session.flush()
        return account
