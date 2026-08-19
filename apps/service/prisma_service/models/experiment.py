"""Contracts for running and reviewing a persisted test session."""

from pydantic import Field
from .base import ApiModel


class SessionCreate(ApiModel):
    collection_id: str
    random_seed: str | None = None


class ResponseWrite(ApiModel):
    selected_item_id: str | None = None
    reaction_time_ms: float | None = Field(default=None, ge=0)
    timed_out: bool = False


class ComparisonView(ApiModel):
    presentation_index: int
    level_index: int
    is_training: bool
    left_item_id: str
    right_item_id: str
    left_type_id: str
    right_type_id: str
    left_type_name: str
    right_type_name: str
    selected_type_name: str | None
    left_image_url: str
    right_image_url: str
    selected_item_id: str | None
    selected_type_id: str | None
    reaction_time_ms: float | None
    exceeded_time_limit: bool
    timed_out: bool
    status: str
    shown_at: str | None
    answered_at: str | None


class SessionView(ApiModel):
    id: str
    account_id: str
    user_name: str
    collection_id: str | None
    collection_name: str
    status: str
    time_mode: str
    time_limit_ms: int | None
    random_seed: str
    started_at: str
    finished_at: str | None
    training_total: int
    training_completed: int
    main_total: int
    main_completed: int
    next_comparison: ComparisonView | None
    comparisons: list[ComparisonView] | None = None
    analysis: dict | None = None
