"""Authentication and current-account HTTP contracts."""

from .base import ApiModel


class LoginRequest(ApiModel):
    login: str
    password: str


class AccountView(ApiModel):
    id: str
    login: str
    full_name: str
    roles: list[str]
    is_active: bool


class LoginResponse(ApiModel):
    access_token: str
    account: AccountView
