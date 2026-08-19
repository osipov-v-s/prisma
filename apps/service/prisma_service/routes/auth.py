"""Login endpoints for the local Desktop service."""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from prisma.persistence.database import get_database_session
from prisma.persistence.repositories import AccountRepository
from prisma.security import verify_password
from ..auth import account_role_names, current_account, token_store
from ..models.auth import AccountView, LoginRequest, LoginResponse


router = APIRouter(prefix="/auth", tags=["authentication"])


def account_view(account) -> AccountView:
    return AccountView(id=account.id, login=account.login,
                       full_name=account.profile.full_name,
                       roles=account_role_names(account), is_active=account.is_active)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, database: Session = Depends(get_database_session)):
    account = AccountRepository(database).find_by_login(payload.login)
    if account is None or not account.is_active or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный логин или пароль.")
    return LoginResponse(access_token=token_store.issue(account.id), account=account_view(account))


@router.get("/me", response_model=AccountView)
def me(account=Depends(current_account)):
    return account_view(account)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(authorization: str | None = Header(default=None)):
    if authorization and authorization.startswith("Bearer "):
        token_store.revoke(authorization.removeprefix("Bearer ").strip())
