"""Persistent experiment snapshots, presented pairs, responses, and analyses."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .collection import Collection, new_id, utc_now


class TestSession(Base):
    __tablename__ = "test_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    collection_id: Mapped[str | None] = mapped_column(
        ForeignKey("collections.id", ondelete="SET NULL"), nullable=True
    )
    collection_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="training")
    time_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    time_limit_ms: Mapped[int | None] = mapped_column(Integer)
    random_seed: Mapped[str] = mapped_column(String(100), nullable=False)

    account: Mapped["Account"] = relationship(back_populates="sessions")
    collection: Mapped[Collection | None] = relationship()
    comparisons: Mapped[list["ComparisonResponse"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ComparisonResponse.presentation_index",
    )
    analysis_results: Mapped[list["AnalysisResult"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class ComparisonResponse(Base):
    """One scheduled presentation; response columns stay null until answered."""

    __tablename__ = "comparison_responses"
    __table_args__ = (
        UniqueConstraint("session_id", "presentation_index", name="uq_session_order"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("test_sessions.id", ondelete="CASCADE"), nullable=False
    )
    presentation_index: Mapped[int] = mapped_column(Integer, nullable=False)
    level_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_training: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    left_item_id: Mapped[str] = mapped_column(String(36), nullable=False)
    right_item_id: Mapped[str] = mapped_column(String(36), nullable=False)
    left_type_id: Mapped[str] = mapped_column(String(36), nullable=False)
    right_type_id: Mapped[str] = mapped_column(String(36), nullable=False)
    selected_item_id: Mapped[str | None] = mapped_column(String(36))
    selected_type_id: Mapped[str | None] = mapped_column(String(36))
    reaction_time_ms: Mapped[float | None] = mapped_column(Float)
    exceeded_time_limit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    timed_out: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    shown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    session: Mapped[TestSession] = relationship(back_populates="comparisons")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    __table_args__ = (
        UniqueConstraint("session_id", "analysis_mode", name="uq_session_analysis_mode"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("test_sessions.id", ondelete="CASCADE"), nullable=False
    )
    analysis_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(100), nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    session: Mapped[TestSession] = relationship(back_populates="analysis_results")


from .account import Account  # noqa: E402
