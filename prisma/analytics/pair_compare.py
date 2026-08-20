"""Scientific baseline for repeated pair observations across collection depth."""

from __future__ import annotations

from dataclasses import replace
from itertools import combinations
import math
from typing import Sequence

import numpy as np

from .exceptions import AnalyticsValidationError
from .models import (
    AnalysisMode,
    CollectionSchema,
    ConsistencyResult,
    Identifier,
    IterationStrategy,
    IterationTrace,
    ModeAnalysis,
    ObservationTrace,
    PairAggregation,
    PairResponse,
    RankedScore,
    ResponseStatus,
    SerializedMatrix,
    SessionAnalysis,
    SessionMetadata,
    TimeAlgorithm,
    TypeChoiceCount,
)


ALGORITHM_VERSION = "prisma-analytics/0.6.0-level-majority"
CONSISTENCY_THRESHOLD = 0.5
FASTEST_MAJORITY_OBSERVATIONS = 2


def analyze_session(
    responses: Sequence[PairResponse],
    collection_schema: CollectionSchema,
    mode: AnalysisMode | str = AnalysisMode.CHOICE_ONLY,
    time_algorithm: TimeAlgorithm | str = TimeAlgorithm.SOURCE_V1,
    iteration_strategy: IterationStrategy | str | None = None,
    epsilon: float = 0.001,
    max_iterations: int = 10_000,
) -> ModeAnalysis:
    """Analyze one collection after aggregating repeated pairs across depth."""

    selected_mode = _coerce_enum(mode, AnalysisMode, "mode")
    selected_time_algorithm = _coerce_enum(
        time_algorithm, TimeAlgorithm, "time_algorithm"
    )
    selected_iteration_strategy = (
        _coerce_enum(iteration_strategy, IterationStrategy, "iteration_strategy")
        if iteration_strategy is not None
        else (
            IterationStrategy.SELF_RETENTION_PROTOTYPE_V1
            if selected_mode is AnalysisMode.CHOICE_ONLY
            else IterationStrategy.LITERAL_SOURCE_V1
        )
    )
    _validate_options(epsilon, max_iterations)
    ordered_responses = _validate_inputs(responses, collection_schema)
    aggregations = _aggregate_validated_pair_observations(
        ordered_responses, collection_schema
    )
    total_pairs = len(aggregations)
    majority_resolved = [
        aggregation
        for aggregation in aggregations
        if aggregation.majority_type_id is not None
    ]
    time_selected = [
        aggregation
        for aggregation in aggregations
        if aggregation.status == "resolved"
    ]
    unresolved_count = total_pairs - len(majority_resolved)
    common = dict(
        mode=selected_mode,
        time_algorithm=(
            selected_time_algorithm
            if selected_mode is AnalysisMode.CHOICE_AND_TIME
            else None
        ),
        iteration_strategy=selected_iteration_strategy,
        pair_aggregations=aggregations,
        resolved_pairs=len(majority_resolved),
        time_selected_pairs=len(time_selected),
        unresolved_pairs=unresolved_count,
        total_pairs=total_pairs,
        coverage=(len(majority_resolved) / total_pairs if total_pairs else 0.0),
        epsilon=epsilon,
        max_iterations=max_iterations,
    )

    if unresolved_count:
        return ModeAnalysis(
            status="insufficient_data",
            message="Недостаточно данных для определения большинства по всем парам.",
            overall=None,
            binary_matrix=None,
            pair_time_matrix_ms=None,
            time_weighted_matrix=None,
            validation_total_time_ms=None,
            consistency=None,
            iteration=None,
            warnings=[
                "At least one pair is incomplete or has no strict majority; no choices were imputed."
            ],
            **common,
        )

    type_ids = [stimulus_type.type_id for stimulus_type in collection_schema.types]
    binary = build_collection_binary_matrix(aggregations, type_ids)
    consistency = calculate_consistency(binary)
    pair_time_matrix = (
        build_pair_time_matrix(aggregations, type_ids)
        if len(time_selected) == total_pairs
        else None
    )
    total_validation_time = (
        compute_validation_total_time(aggregations)
        if len(time_selected) == total_pairs
        else None
    )

    if (
        consistency.zeta is not None
        and consistency.zeta < CONSISTENCY_THRESHOLD
    ):
        return ModeAnalysis(
            status="preferences_not_identified",
            message="Предпочтения не выявлены",
            overall=None,
            binary_matrix=_serialize_matrix(binary),
            pair_time_matrix_ms=(
                _serialize_matrix(pair_time_matrix)
                if pair_time_matrix is not None
                else None
            ),
            time_weighted_matrix=None,
            validation_total_time_ms=total_validation_time,
            consistency=consistency,
            iteration=None,
            warnings=[
                "Zeta is below 0.5; ranking is not calculated by the approved policy."
            ],
            **common,
        )

    if collection_schema.width == 2:
        counts = {
            item.type_id: item.count
            for item in aggregations[0].choice_counts
        }
        vector = [counts[type_id] / collection_schema.depth for type_id in type_ids]
        weighted_width_two = None
        warnings = [
            "Width=2 uses observed choice frequencies; triad consistency is not applicable."
        ]
        message = None
        if selected_mode is AnalysisMode.CHOICE_AND_TIME:
            if pair_time_matrix is not None and total_validation_time is not None:
                weighted_width_two = build_time_weighted_matrix(
                    binary,
                    pair_time_matrix,
                    total_validation_time,
                    selected_time_algorithm,
                )
            message = (
                "Для двух типов показаны фактические проценты выборов; "
                "временная поправка не изменяет итоговый процент."
            )
            warnings.append(
                "Time weighting is retained as a diagnostic matrix only for width=2."
            )
        return ModeAnalysis(
            status="calculated_width_2_frequency",
            message=message,
            overall=_make_scores(vector, collection_schema),
            binary_matrix=_serialize_matrix(binary),
            pair_time_matrix_ms=(
                _serialize_matrix(pair_time_matrix)
                if pair_time_matrix is not None
                else None
            ),
            time_weighted_matrix=(
                _serialize_matrix(weighted_width_two)
                if weighted_width_two is not None
                else None
            ),
            validation_total_time_ms=total_validation_time,
            consistency=consistency,
            iteration=None,
            warnings=warnings,
            **common,
        )

    matrix = binary
    weighted: np.ndarray | None = None
    if selected_mode is AnalysisMode.CHOICE_AND_TIME:
        if pair_time_matrix is None or total_validation_time is None:
            return ModeAnalysis(
                status="insufficient_time_data",
                message=(
                    "Невозможно выбрать два быстрых наблюдения большинства "
                    "для каждой пары."
                ),
                overall=None,
                binary_matrix=_serialize_matrix(binary),
                pair_time_matrix_ms=None,
                time_weighted_matrix=None,
                validation_total_time_ms=None,
                consistency=consistency,
                iteration=None,
                warnings=[
                    "Each pair needs at least two answered majority observations for time analysis."
                ],
                **common,
            )
        weighted = build_time_weighted_matrix(
            binary,
            pair_time_matrix,
            total_validation_time,
            selected_time_algorithm,
        )
        matrix = weighted

    iteration = iterate_rank_weights(
        matrix,
        epsilon=epsilon,
        max_iterations=max_iterations,
        strategy=selected_iteration_strategy,
    )
    if not iteration.converged:
        return ModeAnalysis(
            status="NON_CONVERGED",
            message="Итерационный расчёт не сошёлся.",
            overall=None,
            binary_matrix=_serialize_matrix(binary),
            pair_time_matrix_ms=(
                _serialize_matrix(pair_time_matrix)
                if pair_time_matrix is not None
                else None
            ),
            time_weighted_matrix=(
                _serialize_matrix(weighted) if weighted is not None else None
            ),
            validation_total_time_ms=total_validation_time,
            consistency=consistency,
            iteration=iteration,
            warnings=[iteration.warning] if iteration.warning else [],
            **common,
        )

    return ModeAnalysis(
        status="calculated",
        message=None,
        overall=_make_scores(iteration.final_vector, collection_schema),
        binary_matrix=_serialize_matrix(binary),
        pair_time_matrix_ms=(
            _serialize_matrix(pair_time_matrix)
            if pair_time_matrix is not None
            else None
        ),
        time_weighted_matrix=(
            _serialize_matrix(weighted) if weighted is not None else None
        ),
        validation_total_time_ms=total_validation_time,
        consistency=consistency,
        iteration=iteration,
        warnings=[],
        **common,
    )


def compare_analysis_modes(
    responses: Sequence[PairResponse],
    collection_schema: CollectionSchema,
    time_algorithm: TimeAlgorithm | str = TimeAlgorithm.SOURCE_V1,
    iteration_strategy: IterationStrategy | str | None = None,
    epsilon: float = 0.001,
    max_iterations: int = 10_000,
    session_metadata: SessionMetadata | None = None,
) -> SessionAnalysis:
    """Return independent choice-only and time-weighted collection results."""

    choice_only = analyze_session(
        responses,
        collection_schema,
        mode=AnalysisMode.CHOICE_ONLY,
        time_algorithm=time_algorithm,
        iteration_strategy=iteration_strategy,
        epsilon=epsilon,
        max_iterations=max_iterations,
    )
    choice_and_time = analyze_session(
        responses,
        collection_schema,
        mode=AnalysisMode.CHOICE_AND_TIME,
        time_algorithm=time_algorithm,
        iteration_strategy=iteration_strategy,
        epsilon=epsilon,
        max_iterations=max_iterations,
    )
    session_ids = {response.session_id for response in responses}
    inferred_session_id = next(iter(session_ids)) if session_ids else None
    if session_metadata is not None:
        if session_metadata.collection_id != collection_schema.collection_id:
            raise AnalyticsValidationError(
                "Session metadata collection_id does not match the schema."
            )
        if (
            inferred_session_id is not None
            and session_metadata.session_id != inferred_session_id
        ):
            raise AnalyticsValidationError(
                "Session metadata session_id does not match the responses."
            )
    warnings = list(dict.fromkeys(choice_only.warnings + choice_and_time.warnings))
    return SessionAnalysis(
        session_id=(
            session_metadata.session_id
            if session_metadata is not None
            else inferred_session_id
        ),
        collection_id=collection_schema.collection_id,
        random_seed=session_metadata.random_seed if session_metadata else None,
        algorithm_version=ALGORITHM_VERSION,
        source_responses=list(responses),
        choice_only=choice_only,
        choice_and_time=choice_and_time,
        warnings=warnings,
    )


def aggregate_pair_observations(
    responses: Sequence[PairResponse], collection_schema: CollectionSchema
) -> list[PairAggregation]:
    """Aggregate one same-level observation per column into a pair majority.

    Stimuli are compared only inside their own level. Levels are joined only
    after presentation, when the odd number of answers determines the winner
    for each unordered pair of types.
    """

    ordered = _validate_inputs(responses, collection_schema)
    return _aggregate_validated_pair_observations(ordered, collection_schema)


def _aggregate_validated_pair_observations(
    responses: Sequence[PairResponse], collection_schema: CollectionSchema
) -> list[PairAggregation]:
    type_ids = [stimulus_type.type_id for stimulus_type in collection_schema.types]
    grouped: dict[frozenset[Identifier], list[PairResponse]] = {}
    for response in responses:
        grouped.setdefault(
            _pair_key(response.left_type_id, response.right_type_id), []
        ).append(response)

    results: list[PairAggregation] = []
    for first, second in combinations(type_ids, 2):
        observations = sorted(
            grouped.get(_pair_key(first, second), []),
            key=lambda response: response.comparison_index,
        )
        answered = [
            response
            for response in observations
            if response.status is ResponseStatus.ANSWERED
        ]
        timeouts = [
            response
            for response in observations
            if response.status is ResponseStatus.TIMEOUT
        ]
        counts = {
            first: sum(response.selected_type_id == first for response in answered),
            second: sum(response.selected_type_id == second for response in answered),
        }
        choice_counts = [
            TypeChoiceCount(first, counts[first]),
            TypeChoiceCount(second, counts[second]),
        ]

        if len(observations) != collection_schema.depth or len(answered) != collection_schema.depth:
            trace = [
                _observation_trace(
                    response,
                    "timeout" if response.status is ResponseStatus.TIMEOUT else "not_used_incomplete_pair",
                )
                for response in observations
            ]
            results.append(
                PairAggregation(
                    first_type_id=first,
                    second_type_id=second,
                    status="incomplete_pair",
                    choice_counts=choice_counts,
                    answered_observations=len(answered),
                    timeout_observations=len(timeouts),
                    expected_observations=collection_schema.depth,
                    majority_type_id=None,
                    majority_count=0,
                    selected_observations=[],
                    observations=trace,
                    reason="Every depth level must contain an answered observation for this pair.",
                )
            )
            continue

        if counts[first] == counts[second]:
            results.append(
                PairAggregation(
                    first_type_id=first,
                    second_type_id=second,
                    status="unresolved_tie",
                    choice_counts=choice_counts,
                    answered_observations=len(answered),
                    timeout_observations=0,
                    expected_observations=collection_schema.depth,
                    majority_type_id=None,
                    majority_count=counts[first],
                    selected_observations=[],
                    observations=[
                        _observation_trace(response, "tie_observation")
                        for response in observations
                    ],
                    reason="The pair has no strict majority.",
                )
            )
            continue

        majority = first if counts[first] > counts[second] else second
        majority_observations = [
            response for response in answered if response.selected_type_id == majority
        ]
        fastest_by_time = sorted(
            majority_observations,
            key=lambda response: (
                float(response.reaction_time_ms),
                response.comparison_index,
            ),
        )[:FASTEST_MAJORITY_OBSERVATIONS]
        # The workbook places the two retained observations into opposite
        # cells in their original presentation order, not in speed order.
        fastest = sorted(
            fastest_by_time,
            key=lambda response: response.comparison_index,
        )
        fastest_indices = {response.comparison_index for response in fastest}
        trace: list[ObservationTrace] = []
        for response in observations:
            if response.comparison_index in fastest_indices:
                role = "selected_fastest_majority"
            elif response.selected_type_id == majority:
                role = "discarded_slower_majority"
            else:
                role = "discarded_minority"
            trace.append(_observation_trace(response, role))

        enough_for_time = len(fastest) == FASTEST_MAJORITY_OBSERVATIONS
        selected_trace = [
            _observation_trace(response, "selected_fastest_majority")
            for response in fastest
        ]
        results.append(
            PairAggregation(
                first_type_id=first,
                second_type_id=second,
                status=(
                    "resolved"
                    if enough_for_time
                    else "majority_resolved_insufficient_time_observations"
                ),
                choice_counts=choice_counts,
                answered_observations=len(answered),
                timeout_observations=0,
                expected_observations=collection_schema.depth,
                majority_type_id=majority,
                majority_count=len(majority_observations),
                selected_observations=selected_trace,
                observations=trace,
                reason=(
                    None
                    if enough_for_time
                    else "Fewer than two majority observations are available."
                ),
            )
        )
    return results


def build_collection_binary_matrix(
    aggregations: Sequence[PairAggregation], type_ids: Sequence[Identifier]
) -> np.ndarray:
    """Build one collection P from majority winners of repeated pair observations."""

    index = {type_id: position for position, type_id in enumerate(type_ids)}
    matrix = np.full((len(type_ids), len(type_ids)), np.nan, dtype=float)
    for aggregation in aggregations:
        if aggregation.majority_type_id is None:
            raise AnalyticsValidationError(
                "Cannot build P while an unordered pair has no majority winner."
            )
        first = index[aggregation.first_type_id]
        second = index[aggregation.second_type_id]
        winner = index[aggregation.majority_type_id]
        loser = second if winner == first else first
        matrix[winner, loser] = 1.0
        matrix[loser, winner] = 0.0
    _validate_binary_complements(matrix)
    return matrix


def build_pair_time_matrix(
    aggregations: Sequence[PairAggregation], type_ids: Sequence[Identifier]
) -> np.ndarray:
    """Place the two retained times in opposite cells of each type pair."""

    index = {type_id: position for position, type_id in enumerate(type_ids)}
    matrix = np.full((len(type_ids), len(type_ids)), np.nan, dtype=float)
    for aggregation in aggregations:
        selected = aggregation.selected_observations
        if len(selected) != FASTEST_MAJORITY_OBSERVATIONS:
            raise AnalyticsValidationError(
                "Every pair needs two fastest majority observations for T_ij cells."
            )
        times = [item.reaction_time_ms for item in selected]
        if any(value is None for value in times):
            raise AnalyticsValidationError(
                "Every selected majority observation must have reaction_time_ms."
            )
        first = index[aggregation.first_type_id]
        second = index[aggregation.second_type_id]
        matrix[first, second] = float(times[0])
        matrix[second, first] = float(times[1])
    return matrix


def compute_validation_total_time(
    aggregations: Sequence[PairAggregation],
) -> float:
    """Compute T as the sum of all retained directed-cell times."""

    if not aggregations or any(
        len(item.selected_observations) != FASTEST_MAJORITY_OBSERVATIONS
        for item in aggregations
    ):
        raise AnalyticsValidationError(
            "Every pair must have two retained observations before computing T."
        )
    selected_times = [
        observation.reaction_time_ms
        for item in aggregations
        for observation in item.selected_observations
    ]
    if any(value is None for value in selected_times):
        raise AnalyticsValidationError(
            "Every retained observation must have reaction_time_ms."
        )
    total = sum(float(value) for value in selected_times if value is not None)
    if not math.isfinite(total) or total <= 0:
        raise AnalyticsValidationError("Validation total time T must be positive and finite.")
    return total


def build_time_weighted_matrix(
    binary: np.ndarray,
    pair_times_ms: np.ndarray,
    total_validation_time_ms: float,
    algorithm: TimeAlgorithm | str = TimeAlgorithm.SOURCE_V1,
) -> np.ndarray:
    """Build P* from the two directed times retained for every pair."""

    selected_algorithm = _coerce_enum(algorithm, TimeAlgorithm, "algorithm")
    total_time = float(total_validation_time_ms)
    if not math.isfinite(total_time) or total_time <= 0:
        raise AnalyticsValidationError("total_validation_time_ms must be positive and finite.")
    size = binary.shape[0]
    weighted = np.full_like(binary, np.nan, dtype=float)
    for i in range(size):
        for j in range(i + 1, size):
            weighted[i, j] = _weighted_cell(
                binary[i, j], pair_times_ms[i, j], total_time
            )
            if selected_algorithm is TimeAlgorithm.SOURCE_V1:
                weighted[j, i] = _weighted_cell(
                    binary[j, i], pair_times_ms[j, i], total_time
                )
            else:
                weighted[j, i] = 1.0 - weighted[i, j]
    return weighted


def _weighted_cell(binary_value: float, time_ms: float, total_time_ms: float) -> float:
    """Apply the workbook formula to one directed off-diagonal cell."""

    directed_time = float(time_ms)
    if (
        not math.isfinite(directed_time)
        or directed_time <= 0
        or directed_time > total_time_ms
    ):
        raise AnalyticsValidationError(
            "Every directed T_ij must be positive, finite, and no greater than T."
        )
    coefficient = 1.0 - directed_time / total_time_ms
    return (
        binary_value * coefficient
        + (1.0 - binary_value) * (1.0 - coefficient)
    )


def calculate_consistency(
    binary: np.ndarray, scope: str = "collection"
) -> ConsistencyResult:
    """Count cyclic triads of the single majority matrix P."""

    size = binary.shape[0]
    cyclic = 0
    for i, j, k in combinations(range(size), 3):
        cycle_sum = binary[i, j] + binary[j, k] + binary[k, i]
        if cycle_sum == 0.0 or cycle_sum == 3.0:
            cyclic += 1
    maximum = (
        size * (size**2 - 1) // 24
        if size % 2
        else size * (size**2 - 4) // 24
    )
    if maximum == 0:
        return ConsistencyResult(
            scope=scope,
            cyclic_triads=cyclic,
            maximum_cyclic_triads=maximum,
            zeta=None,
            classification="not_applicable",
            interpretation=None,
            reason="Cmax is zero for width=2; zeta is undefined.",
        )
    zeta = 1.0 - cyclic / maximum
    classification, interpretation = _classify_consistency(zeta)
    return ConsistencyResult(
        scope=scope,
        cyclic_triads=cyclic,
        maximum_cyclic_triads=maximum,
        zeta=zeta,
        classification=classification,
        interpretation=interpretation,
    )


def iterate_rank_weights(
    matrix: np.ndarray,
    epsilon: float = 0.001,
    max_iterations: int = 10_000,
    strategy: IterationStrategy | str = (
        IterationStrategy.SELF_RETENTION_PROTOTYPE_V1
    ),
) -> IterationTrace:
    """Calculate each new w_i as an explicit weighted sum over one row."""

    _validate_options(epsilon, max_iterations)
    selected_strategy = _coerce_enum(strategy, IterationStrategy, "strategy")
    size = matrix.shape[0]
    numeric_matrix = np.nan_to_num(matrix, nan=0.0)
    # The reference workbook starts from W(0) = [1, ..., 1].  Later vectors
    # are normalized after each complete row-wise step.
    previous = np.ones(size, dtype=float)
    initial = previous.tolist()
    normalized_vectors: list[list[float]] = []
    raw_vectors: list[list[float]] = []
    final_delta: float | None = None
    for iteration in range(1, max_iterations + 1):
        raw = calculate_next_raw_weights(
            numeric_matrix, previous, strategy=selected_strategy
        )
        raw_vectors.append(raw.tolist())
        total = float(np.sum(raw))
        if (
            not np.all(np.isfinite(raw))
            or np.any(raw < 0)
            or not math.isfinite(total)
            or total <= 0
        ):
            warning = (
                "Row-wise iteration produced invalid values or a non-positive "
                "normalization sum; the last normalized vector is returned."
            )
            return IterationTrace(
                strategy=selected_strategy,
                converged=False,
                status="zero_normalization_sum",
                iterations=iteration,
                epsilon=epsilon,
                max_iterations=max_iterations,
                final_delta=final_delta,
                initial_vector=initial,
                final_vector=previous.tolist(),
                normalized_vectors=normalized_vectors,
                raw_vectors=raw_vectors,
                warning=warning,
            )
        current = raw / total
        final_delta = float(np.max(np.abs(current - previous)))
        normalized_vectors.append(current.tolist())
        if final_delta < epsilon:
            return IterationTrace(
                strategy=selected_strategy,
                converged=True,
                status="converged",
                iterations=iteration,
                epsilon=epsilon,
                max_iterations=max_iterations,
                final_delta=final_delta,
                initial_vector=initial,
                final_vector=current.tolist(),
                normalized_vectors=normalized_vectors,
                raw_vectors=raw_vectors,
            )
        previous = current
    return IterationTrace(
        strategy=selected_strategy,
        converged=False,
        status="max_iterations_reached",
        iterations=max_iterations,
        epsilon=epsilon,
        max_iterations=max_iterations,
        final_delta=final_delta,
        initial_vector=initial,
        final_vector=previous.tolist(),
        normalized_vectors=normalized_vectors,
        raw_vectors=raw_vectors,
        warning="Maximum iteration count reached before convergence.",
    )


def calculate_next_raw_weights(
    matrix: np.ndarray,
    previous_vector: Sequence[float],
    strategy: IterationStrategy | str = IterationStrategy.LITERAL_SOURCE_V1,
) -> np.ndarray:
    """Return raw w_i values by explicit element products and row sums."""

    selected_strategy = _coerce_enum(strategy, IterationStrategy, "strategy")
    numeric_matrix = np.nan_to_num(np.asarray(matrix, dtype=float), nan=0.0)
    previous = np.asarray(previous_vector, dtype=float)
    if numeric_matrix.ndim != 2 or numeric_matrix.shape[0] != numeric_matrix.shape[1]:
        raise AnalyticsValidationError("The iteration matrix must be square.")
    if previous.ndim != 1 or len(previous) != numeric_matrix.shape[0]:
        raise AnalyticsValidationError(
            "previous_vector length must equal the matrix width."
        )
    raw = np.zeros(len(previous), dtype=float)
    for i in range(len(previous)):
        row_total = (
            previous[i]
            if selected_strategy
            is IterationStrategy.SELF_RETENTION_PROTOTYPE_V1
            else 0.0
        )
        for j in range(len(previous)):
            if i == j:
                continue
            row_total += numeric_matrix[i, j] * previous[j]
        raw[i] = row_total
    return raw


def _validate_inputs(
    responses: Sequence[PairResponse], schema: CollectionSchema
) -> list[PairResponse]:
    if schema.depth < 1 or schema.depth % 2 == 0:
        raise AnalyticsValidationError("Collection depth must be a positive odd integer.")
    if schema.width < 2:
        raise AnalyticsValidationError("Collection width must be at least 2.")
    type_ids = [item.type_id for item in schema.types]
    if len(type_ids) != len(set(type_ids)):
        raise AnalyticsValidationError("Type identifiers must be unique.")
    if any(not item.name.strip() for item in schema.types):
        raise AnalyticsValidationError("Type names must not be blank.")
    item_ids = [item.item_id for item in schema.items]
    if len(item_ids) != len(set(item_ids)):
        raise AnalyticsValidationError("Collection item identifiers must be unique.")
    item_lookup = {item.item_id: item for item in schema.items}
    expected_slots = {
        (type_id, level)
        for type_id in type_ids
        for level in range(1, schema.depth + 1)
    }
    actual_slots = {(item.type_id, item.level_index) for item in schema.items}
    if len(actual_slots) != len(schema.items) or actual_slots != expected_slots:
        raise AnalyticsValidationError(
            "Collection schema must contain exactly one item for every type and level."
        )
    session_ids = {response.session_id for response in responses}
    if len(session_ids) > 1:
        raise AnalyticsValidationError("All responses must belong to one session.")
    comparison_indices = [response.comparison_index for response in responses]
    if len(comparison_indices) != len(set(comparison_indices)):
        raise AnalyticsValidationError("comparison_index must be unique within a session.")

    seen_pairs: set[tuple[int, frozenset[Identifier]]] = set()
    normalized: list[PairResponse] = []
    for original in responses:
        response = original
        if response.collection_id != schema.collection_id:
            raise AnalyticsValidationError("Response collection_id does not match the schema.")
        if response.level_index not in range(1, schema.depth + 1):
            raise AnalyticsValidationError("Response level_index is outside collection depth.")
        if response.comparison_index < 1:
            raise AnalyticsValidationError("comparison_index must be positive.")
        if response.left_item_id not in item_lookup or response.right_item_id not in item_lookup:
            raise AnalyticsValidationError("Response references an unknown collection item.")
        left_item = item_lookup[response.left_item_id]
        right_item = item_lookup[response.right_item_id]
        if left_item.level_index != right_item.level_index:
            raise AnalyticsValidationError(
                "Items from different level_index values must never be compared."
            )
        if left_item.level_index != response.level_index:
            raise AnalyticsValidationError("Response level_index does not match its items.")
        if left_item.type_id != response.left_type_id or right_item.type_id != response.right_type_id:
            raise AnalyticsValidationError("Item/type fields are inconsistent.")
        if response.left_type_id == response.right_type_id:
            raise AnalyticsValidationError("A response must compare two different types.")
        marker = (
            response.level_index,
            _pair_key(response.left_type_id, response.right_type_id),
        )
        if marker in seen_pairs:
            raise AnalyticsValidationError(
                "A type pair may appear only once within a level, including timeouts."
            )
        seen_pairs.add(marker)

        status = _coerce_enum(response.status, ResponseStatus, "response.status")
        if status is not response.status:
            response = replace(response, status=status)
        if status is ResponseStatus.ANSWERED:
            valid = {
                (response.left_item_id, response.left_type_id),
                (response.right_item_id, response.right_type_id),
            }
            if (response.selected_item_id, response.selected_type_id) not in valid:
                raise AnalyticsValidationError(
                    "An answered response must select one shown item and its type."
                )
            if response.timed_out:
                raise AnalyticsValidationError("An answered response cannot have timed_out=true.")
            if response.reaction_time_ms is None or not _positive_finite(response.reaction_time_ms):
                raise AnalyticsValidationError(
                    "An answered response requires positive finite reaction_time_ms."
                )
        else:
            if response.selected_item_id is not None or response.selected_type_id is not None:
                raise AnalyticsValidationError("A timeout response must not contain a selection.")
            if not response.timed_out:
                raise AnalyticsValidationError("A timeout response requires timed_out=true.")
        if response.time_limit_ms is not None and not _positive_finite(response.time_limit_ms):
            raise AnalyticsValidationError("time_limit_ms must be positive when provided.")
        normalized.append(response)
    return sorted(normalized, key=lambda response: response.comparison_index)


def _validate_binary_complements(matrix: np.ndarray) -> None:
    for i in range(matrix.shape[0]):
        for j in range(i + 1, matrix.shape[1]):
            if matrix[i, j] + matrix[j, i] != 1.0:
                raise AnalyticsValidationError(
                    "Invalid pair matrix: p_ij + p_ji must equal 1; calculation stopped."
                )


def _validate_options(epsilon: float, max_iterations: int) -> None:
    if not _positive_finite(epsilon):
        raise AnalyticsValidationError("epsilon must be finite and greater than zero.")
    if not isinstance(max_iterations, int) or isinstance(max_iterations, bool) or max_iterations < 1:
        raise AnalyticsValidationError("max_iterations must be a positive integer.")


def _positive_finite(value: float) -> bool:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(numeric) and numeric > 0


def _pair_key(left: Identifier, right: Identifier) -> frozenset[Identifier]:
    return frozenset((left, right))


def _observation_trace(response: PairResponse, role: str) -> ObservationTrace:
    return ObservationTrace(
        level_index=response.level_index,
        comparison_index=response.comparison_index,
        left_item_id=response.left_item_id,
        right_item_id=response.right_item_id,
        left_type_id=response.left_type_id,
        right_type_id=response.right_type_id,
        selected_item_id=response.selected_item_id,
        selected_type_id=response.selected_type_id,
        reaction_time_ms=(
            float(response.reaction_time_ms)
            if response.reaction_time_ms is not None
            else None
        ),
        time_limit_ms=(
            float(response.time_limit_ms)
            if response.time_limit_ms is not None
            else None
        ),
        exceeded_time_limit=response.exceeded_time_limit,
        timed_out=response.timed_out,
        status=response.status,
        role=role,
    )


def _serialize_matrix(matrix: np.ndarray) -> SerializedMatrix:
    return [
        [None if math.isnan(float(value)) else float(value) for value in row]
        for row in matrix
    ]


def _make_scores(
    vector: Sequence[float], collection_schema: CollectionSchema
) -> list[RankedScore]:
    return [
        RankedScore(
            type_id=stimulus_type.type_id,
            type_name=stimulus_type.name,
            score=float(score),
            percent=float(score) * 100.0,
        )
        for stimulus_type, score in zip(collection_schema.types, vector, strict=True)
    ]


def _classify_consistency(zeta: float) -> tuple[str, str | None]:
    if zeta >= 0.90:
        return "excellent", "Предпочтения сформированы"
    if zeta >= 0.70:
        return "good", "Предпочтения устойчивые"
    if zeta >= 0.50:
        return "moderate", "Предпочтения выявлены"
    if zeta >= 0.20:
        return "low", None
    return "critical", None


def _coerce_enum(value, enum_type, field_name: str):
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        allowed = ", ".join(item.value for item in enum_type)
        raise AnalyticsValidationError(
            f"Unknown {field_name}={value!r}; expected one of: {allowed}."
        ) from error
