"""Adapters between HTTP payloads and mathematical contracts."""

from .analytics import to_collection_schema, to_pair_responses, to_session_metadata

__all__ = [
    "to_collection_schema",
    "to_pair_responses",
    "to_session_metadata",
]
