"""Common type aliases used only by the analytics package."""

from typing import TypeAlias


Identifier: TypeAlias = str | int
SerializedMatrix: TypeAlias = list[list[float | None]]
