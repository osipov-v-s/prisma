"""Single source of truth for non-mathematical application data.

The scientific package keeps its own deliberately isolated input/output models.
Everything else in Desktop uses these small serializable dataclasses.
"""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Account:
    id: str
    login: str
    full_name: str
    roles: list[str]
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CollectionItem:
    id: str
    type_id: str
    level_index: int
    image_path: str | None


@dataclass(slots=True)
class CollectionRow:
    row_index: int
    type_id: str
    type_name: str
    items: list[CollectionItem] = field(default_factory=list)


@dataclass(slots=True)
class Collection:
    id: str
    name: str
    width: int
    depth: int
    is_active: bool
    time_mode: str
    time_limit_ms: int | None
    created_at: str
    updated_at: str
    rows: list[CollectionRow] = field(default_factory=list)


@dataclass(slots=True)
class TestSession:
    id: str
    account_id: str
    collection_id: str | None
    status: str
    time_mode: str
    time_limit_ms: int | None
    random_seed: str
    started_at: str
    finished_at: str | None
