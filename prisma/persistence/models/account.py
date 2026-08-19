"""Accounts, profiles, and roles used by the local Desktop application."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .collection import new_id, utc_now


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    login: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    profile: Mapped["Profile"] = relationship(
        back_populates="account", cascade="all, delete-orphan", uselist=False
    )
    role_links: Mapped[list["AccountRole"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["TestSession"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    patronymic: Mapped[str | None] = mapped_column(String(100), nullable=True)

    account: Mapped[Account] = relationship(back_populates="profile")

    @property
    def full_name(self) -> str:
        return " ".join(
            part for part in (self.last_name, self.first_name, self.patronymic) if part
        )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)

    account_links: Mapped[list["AccountRole"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )


class AccountRole(Base):
    __tablename__ = "account_roles"

    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )

    account: Mapped[Account] = relationship(back_populates="role_links")
    role: Mapped[Role] = relationship(back_populates="account_links")


# Imported only for SQLAlchemy's relationship type resolution.
from .experiment import TestSession  # noqa: E402
