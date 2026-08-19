"""HTTP representation of a collection snapshot used for analysis."""

from pydantic import Field

from .base import ApiModel


class StimulusTypePayload(ApiModel):
    type_id: str | int
    name: str = Field(min_length=1)


class CollectionItemPayload(ApiModel):
    item_id: str | int
    type_id: str | int
    level_index: int = Field(ge=1)


class CollectionSchemaPayload(ApiModel):
    collection_id: str | int
    depth: int = Field(ge=1)
    types: list[StimulusTypePayload]
    items: list[CollectionItemPayload]
