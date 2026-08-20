"""Typed views of frequently used SQLite rows."""

from dataclasses import dataclass


@dataclass(slots=True)
class StoredComparison:
    id: str
    session_id: str
    presentation_index: int
    level_index: int
    left_item_id: str
    right_item_id: str
    left_type_id: str
    right_type_id: str
    status: str


@dataclass(slots=True)
class StoredAnalysis:
    id: str
    session_id: str
    algorithm_version: str
    result_json: str
