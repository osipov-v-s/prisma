"""Settings and top-level contract of the analysis HTTP endpoint."""

from typing import Any

from pydantic import Field

from .base import ApiModel
from .collection import CollectionSchemaPayload
from .session import PairResponsePayload, SessionMetadataPayload


class AnalysisSettingsPayload(ApiModel):
    time_algorithm: str = "source_v1"
    iteration_strategy: str | None = None
    epsilon: float = Field(default=0.001, gt=0)
    max_iterations: int = Field(default=10_000, ge=1)


class CompareAnalysisRequest(ApiModel):
    collection: CollectionSchemaPayload
    responses: list[PairResponsePayload]
    session: SessionMetadataPayload | None = None
    settings: AnalysisSettingsPayload = Field(default_factory=AnalysisSettingsPayload)


AnalysisResponse = dict[str, Any]
