"""Intermediate models describing preprocessing of repeated observations."""

from dataclasses import dataclass

from .common import Identifier
from .enums import ResponseStatus


@dataclass(frozen=True, slots=True)
class ObservationTrace:
    """How one repeated observation was handled by the analytics core."""

    level_index: int
    comparison_index: int
    left_item_id: Identifier
    right_item_id: Identifier
    left_type_id: Identifier
    right_type_id: Identifier
    selected_item_id: Identifier | None
    selected_type_id: Identifier | None
    reaction_time_ms: float | None
    time_limit_ms: float | None
    exceeded_time_limit: bool
    timed_out: bool
    status: ResponseStatus
    role: str


@dataclass(frozen=True, slots=True)
class TypeChoiceCount:
    type_id: Identifier
    count: int


@dataclass(frozen=True, slots=True)
class PairAggregation:
    """Majority and two-fastest trace for one pair across collection depth."""

    first_type_id: Identifier
    second_type_id: Identifier
    status: str
    choice_counts: list[TypeChoiceCount]
    answered_observations: int
    timeout_observations: int
    expected_observations: int
    majority_type_id: Identifier | None
    majority_count: int
    selected_observations: list[ObservationTrace]
    observations: list[ObservationTrace]
    reason: str | None = None
