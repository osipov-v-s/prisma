"""Administrator-facing account contracts."""

from pydantic import Field
from .auth import AccountView
from .base import ApiModel


class UserCreate(ApiModel):
    login: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=200)
    last_name: str = Field(min_length=1, max_length=100)
    first_name: str = Field(min_length=1, max_length=100)
    patronymic: str | None = Field(default=None, max_length=100)
    roles: list[str] = Field(default_factory=lambda: ["USER"])


UserView = AccountView
