"""HTTP models for one test session and its recorded pair responses."""

from pydantic import Field

from .base import ApiModel


class PairResponsePayload(ApiModel):
    session_id: str | int
    collection_id: str | int
    level_index: int = Field(ge=1)
    comparison_index: int = Field(ge=1)
    left_item_id: str | int
    right_item_id: str | int
    left_type_id: str | int
    right_type_id: str | int
    selected_item_id: str | int | None
    selected_type_id: str | int | None
    reaction_time_ms: float | None
    time_limit_ms: float | None = None
    exceeded_time_limit: bool = False
    timed_out: bool = False
    status: str = "answered"


class SessionMetadataPayload(ApiModel):
    session_id: str | int
    collection_id: str | int
    random_seed: str | int | None = None
