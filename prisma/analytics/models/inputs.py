"""Serializable input contracts accepted by the mathematical core."""

from dataclasses import dataclass

from .common import Identifier
from .enums import ResponseStatus


@dataclass(frozen=True, slots=True)
class StimulusType:
    type_id: Identifier
    name: str


@dataclass(frozen=True, slots=True)
class CollectionItem:
    item_id: Identifier
    type_id: Identifier
    level_index: int


@dataclass(frozen=True, slots=True)
class CollectionSchema:
    collection_id: Identifier
    depth: int
    types: tuple[StimulusType, ...]
    items: tuple[CollectionItem, ...]

    @property
    def width(self) -> int:
        return len(self.types)


@dataclass(frozen=True, slots=True)
class SessionMetadata:
    session_id: Identifier
    collection_id: Identifier
    random_seed: Identifier | None


@dataclass(frozen=True, slots=True)
class PairResponse:
    session_id: Identifier
    collection_id: Identifier
    level_index: int
    comparison_index: int
    left_item_id: Identifier
    right_item_id: Identifier
    left_type_id: Identifier
    right_type_id: Identifier
    selected_item_id: Identifier | None
    selected_type_id: Identifier | None
    reaction_time_ms: float | None
    time_limit_ms: float | None = None
    exceeded_time_limit: bool = False
    timed_out: bool = False
    status: ResponseStatus = ResponseStatus.ANSWERED
