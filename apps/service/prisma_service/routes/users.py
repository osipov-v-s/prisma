"""Administrator operations over local user accounts."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from prisma.persistence.database import get_database_session
from prisma.persistence.repositories import AccountRepository
from prisma.security import hash_password
from ..auth import require_admin
from ..models.auth import AccountView
from ..models.users import UserCreate
from .auth import account_view


router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[AccountView])
def list_users(database: Session = Depends(get_database_session)):
    return [account_view(account) for account in AccountRepository(database).list()]


@router.post("", response_model=AccountView, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, database: Session = Depends(get_database_session)):
    roles = tuple(sorted(set(payload.roles)))
    if not roles or any(role not in {"USER", "ADMIN"} for role in roles):
        raise HTTPException(422, "Допустимые роли: USER и ADMIN.")
    repository = AccountRepository(database)
    if repository.find_by_login(payload.login):
        raise HTTPException(409, "Пользователь с таким логином уже существует.")
    account = repository.create(login=payload.login, password_hash=hash_password(payload.password),
                                last_name=payload.last_name, first_name=payload.first_name,
                                patronymic=payload.patronymic, roles=roles)
    database.commit()
    return account_view(repository.get(account.id))


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(account_id: str, database: Session = Depends(get_database_session),
                admin=Depends(require_admin)):
    account = AccountRepository(database).get(account_id)
    if account is None:
        raise HTTPException(404, "Пользователь не найден.")
    if account.id == admin.id:
        raise HTTPException(409, "Нельзя удалить текущую учётную запись.")
    database.delete(account)
    database.commit()
