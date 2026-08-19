"""Normalized SQLAlchemy models for editable stimulus collections."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    time_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    time_limit_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    type_rows: Mapped[list["CollectionType"]] = relationship(
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="CollectionType.row_index",
    )
    items: Mapped[list["CollectionItem"]] = relationship(
        back_populates="collection",
        cascade="all, delete-orphan",
    )


class StimulusType(Base):
    __tablename__ = "stimulus_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)

    collection_rows: Mapped[list["CollectionType"]] = relationship(
        back_populates="stimulus_type"
    )
    items: Mapped[list["CollectionItem"]] = relationship(
        back_populates="stimulus_type"
    )


class CollectionType(Base):
    __tablename__ = "collection_types"
    __table_args__ = (
        UniqueConstraint("collection_id", "row_index", name="uq_collection_row"),
        UniqueConstraint("collection_id", "type_id", name="uq_collection_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    collection_id: Mapped[str] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), nullable=False
    )
    type_id: Mapped[str] = mapped_column(
        ForeignKey("stimulus_types.id", ondelete="RESTRICT"), nullable=False
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)

    collection: Mapped[Collection] = relationship(back_populates="type_rows")
    stimulus_type: Mapped[StimulusType] = relationship(
        back_populates="collection_rows"
    )


class CollectionItem(Base):
    __tablename__ = "collection_items"
    __table_args__ = (
        UniqueConstraint(
            "collection_id",
            "type_id",
            "level_index",
            name="uq_collection_type_level",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    collection_id: Mapped[str] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), nullable=False
    )
    type_id: Mapped[str] = mapped_column(
        ForeignKey("stimulus_types.id", ondelete="RESTRICT"), nullable=False
    )
    level_index: Mapped[int] = mapped_column(Integer, nullable=False)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    collection: Mapped[Collection] = relationship(back_populates="items")
    stimulus_type: Mapped[StimulusType] = relationship(back_populates="items")
