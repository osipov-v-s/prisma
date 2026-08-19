"""Serializable outputs returned by the mathematical core."""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .common import Identifier, SerializedMatrix
from .enums import AnalysisMode, IterationStrategy, TimeAlgorithm
from .inputs import PairResponse
from .observations import PairAggregation


@dataclass(frozen=True, slots=True)
class RankedScore:
    type_id: Identifier
    type_name: str
    score: float
    percent: float


@dataclass(frozen=True, slots=True)
class IterationTrace:
    strategy: IterationStrategy
    converged: bool
    status: str
    iterations: int
    epsilon: float
    max_iterations: int
    final_delta: float | None
    initial_vector: list[float]
    final_vector: list[float]
    normalized_vectors: list[list[float]]
    raw_vectors: list[list[float]]
    warning: str | None = None


@dataclass(frozen=True, slots=True)
class ConsistencyResult:
    scope: str
    cyclic_triads: int | None
    maximum_cyclic_triads: int | None
    zeta: float | None
    classification: str
    interpretation: str | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ModeAnalysis:
    mode: AnalysisMode
    time_algorithm: TimeAlgorithm | None
    iteration_strategy: IterationStrategy
    status: str
    message: str | None
    overall: list[RankedScore] | None
    pair_aggregations: list[PairAggregation]
    binary_matrix: SerializedMatrix | None
    pair_time_matrix_ms: SerializedMatrix | None
    time_weighted_matrix: SerializedMatrix | None
    validation_total_time_ms: float | None
    consistency: ConsistencyResult | None
    iteration: IterationTrace | None
    resolved_pairs: int
    time_selected_pairs: int
    unresolved_pairs: int
    total_pairs: int
    coverage: float
    epsilon: float
    max_iterations: int
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SessionAnalysis:
    session_id: Identifier | None
    collection_id: Identifier
    random_seed: Identifier | None
    algorithm_version: str
    source_responses: list[PairResponse]
    choice_only: ModeAnalysis
    choice_and_time: ModeAnalysis
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return primitives ready for JSON, HTTP, files, or persistence."""

        return _json_ready(asdict(self))


def _json_ready(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value
