"""HTTP contracts for creating and editing collections."""

from typing import Literal

from pydantic import Field, model_validator

from .base import ApiModel


TimeMode = Literal["timeout_skip", "timeout_mark", "no_limit"]


class CollectionRowWrite(ApiModel):
    row_index: int = Field(ge=1)
    type_name: str = ""


class CollectionWrite(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    width: int = Field(ge=2, le=20)
    depth: int = Field(ge=1, le=99)
    time_mode: TimeMode = "timeout_mark"
    time_limit_ms: int | None = Field(default=5_000, ge=1)
    rows: list[CollectionRowWrite] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_editor_shape(self) -> "CollectionWrite":
        if self.depth % 2 == 0:
            raise ValueError("Количество изображений каждого типа должно быть нечётным.")
        row_indices = [row.row_index for row in self.rows]
        if len(row_indices) != len(set(row_indices)):
            raise ValueError("row_index не должен повторяться.")
        if any(index > self.width for index in row_indices):
            raise ValueError("row_index находится за пределами ширины коллекции.")
        if self.time_mode != "no_limit" and self.time_limit_ms is None:
            raise ValueError("Для режима с ограничением необходимо указать время.")
        return self
