from __future__ import annotations

from dataclasses import replace
import json
import math

import numpy as np
import pytest

from prisma.analytics import (
    AnalyticsValidationError,
    CollectionItem,
    CollectionSchema,
    IterationStrategy,
    PairResponse,
    ResponseStatus,
    SessionMetadata,
    StimulusType,
    aggregate_pair_observations,
    analyze_session,
    build_time_weighted_matrix,
    calculate_consistency,
    calculate_next_raw_weights,
    compare_analysis_modes,
    compute_validation_total_time,
    iterate_rank_weights,
)


def make_schema(names: tuple[str, ...], depth: int) -> CollectionSchema:
    types = tuple(StimulusType(index + 1, name) for index, name in enumerate(names))
    items = tuple(
        CollectionItem(f"item-{item.type_id}-{level}", item.type_id, level)
        for level in range(1, depth + 1)
        for item in types
    )
    return CollectionSchema("collection-1", depth, types, items)


def make_responses(
    schema: CollectionSchema,
    winners: dict[frozenset[int], list[int]],
    times: dict[frozenset[int], list[float]] | None = None,
    session_id: str = "session-1",
) -> list[PairResponse]:
    responses: list[PairResponse] = []
    comparison_index = 1
    for level in range(1, schema.depth + 1):
        for left in range(1, schema.width + 1):
            for right in range(left + 1, schema.width + 1):
                pair = frozenset((left, right))
                selected = winners[pair][level - 1]
                reaction_time = (
                    times[pair][level - 1]
                    if times is not None and pair in times
                    else float(100 * level + comparison_index)
                )
                responses.append(
                    PairResponse(
                        session_id=session_id,
                        collection_id=schema.collection_id,
                        level_index=level,
                        comparison_index=comparison_index,
                        left_item_id=f"item-{left}-{level}",
                        right_item_id=f"item-{right}-{level}",
                        left_type_id=left,
                        right_type_id=right,
                        selected_item_id=f"item-{selected}-{level}",
                        selected_type_id=selected,
                        reaction_time_ms=reaction_time,
                    )
                )
                comparison_index += 1
    return responses


def repeat_tournament(
    depth: int, winners: dict[frozenset[int], int]
) -> dict[frozenset[int], list[int]]:
    return {pair: [winner] * depth for pair, winner in winners.items()}


def four_type_moderate_tournament() -> dict[frozenset[int], int]:
    # P upper triangle bits: 0,0,0,0,1,0. One cyclic triad gives zeta=0.5.
    return {
        frozenset((1, 2)): 2,
        frozenset((1, 3)): 3,
        frozenset((1, 4)): 4,
        frozenset((2, 3)): 3,
        frozenset((2, 4)): 2,
        frozenset((3, 4)): 4,
    }


def uniform_times(schema: CollectionSchema, value: float = 10.0):
    return {
        frozenset((left, right)): [value] * schema.depth
        for left in range(1, schema.width + 1)
        for right in range(left + 1, schema.width + 1)
    }


def workbook_example() -> tuple[CollectionSchema, list[PairResponse]]:
    """Recreate the four-profession example from Попарное сравнение.xlsx."""

    schema = make_schema(("Инженер", "Архитектор", "Врач", "Пилот"), depth=5)
    winners = {
        frozenset((1, 2)): [1, 1, 1, 2, 2],
        frozenset((1, 3)): [1, 1, 1, 3, 3],
        frozenset((1, 4)): [1, 1, 1, 4, 4],
        frozenset((2, 3)): [3, 3, 3, 2, 2],
        frozenset((2, 4)): [4, 4, 4, 2, 2],
        frozenset((3, 4)): [3, 3, 3, 4, 4],
    }
    times = {
        frozenset((1, 2)): [2694.0, 2217.0, 9000.0, 1.0, 2.0],
        frozenset((1, 3)): [390.0, 1238.0, 9000.0, 1.0, 2.0],
        frozenset((1, 4)): [1227.0, 1456.0, 9000.0, 1.0, 2.0],
        frozenset((2, 3)): [2400.0, 2549.0, 9000.0, 1.0, 2.0],
        frozenset((2, 4)): [2514.0, 2492.0, 9000.0, 1.0, 2.0],
        frozenset((3, 4)): [1730.0, 2217.0, 9000.0, 1.0, 2.0],
    }
    return schema, make_responses(schema, winners, times)


def incoming_selection_example() -> tuple[CollectionSchema, list[PairResponse]]:
    """Recreate «Входящие данные и их отбор.xlsx» with three columns."""

    schema = make_schema(("Инженер", "Архитектор", "Врач", "Пилот"), depth=3)
    winners = {
        frozenset((1, 2)): [2, 2, 1],
        frozenset((1, 3)): [3, 3, 1],
        frozenset((1, 4)): [1, 4, 4],
        frozenset((2, 3)): [2, 2, 2],
        frozenset((2, 4)): [2, 2, 2],
        frozenset((3, 4)): [3, 4, 4],
    }
    return schema, make_responses(schema, winners)


def test_majority_group_always_selects_exactly_two_fastest_observations() -> None:
    schema = make_schema(("A", "B"), depth=5)
    pair = frozenset((1, 2))
    responses = make_responses(
        schema,
        {pair: [1, 1, 1, 2, 2]},
        {pair: [300.0, 100.0, 200.0, 1.0, 2.0]},
    )

    aggregation = aggregate_pair_observations(responses, schema)[0]

    assert aggregation.majority_type_id == 1
    assert aggregation.majority_count == 3
    assert len(aggregation.selected_observations) == 2
    assert [item.level_index for item in aggregation.selected_observations] == [2, 3]
    assert [item.reaction_time_ms for item in aggregation.selected_observations] == [
        100.0,
        200.0,
    ]
    assert [item.role for item in aggregation.observations] == [
        "discarded_slower_majority",
        "selected_fastest_majority",
        "selected_fastest_majority",
        "discarded_minority",
        "discarded_minority",
    ]


def test_all_five_majority_observations_still_select_only_two() -> None:
    schema = make_schema(("A", "B"), depth=5)
    pair = frozenset((1, 2))
    aggregation = aggregate_pair_observations(
        make_responses(
            schema,
            {pair: [1, 1, 1, 1, 1]},
            {pair: [50.0, 40.0, 30.0, 20.0, 10.0]},
        ),
        schema,
    )[0]
    assert [item.level_index for item in aggregation.selected_observations] == [4, 5]
    assert [item.reaction_time_ms for item in aggregation.selected_observations] == [
        20.0,
        10.0,
    ]


def test_equal_times_use_comparison_index_as_deterministic_tie_breaker() -> None:
    schema = make_schema(("A", "B"), depth=3)
    pair = frozenset((1, 2))
    aggregation = aggregate_pair_observations(
        make_responses(schema, {pair: [1, 1, 1]}, {pair: [10.0, 10.0, 10.0]}),
        schema,
    )[0]
    assert [item.comparison_index for item in aggregation.selected_observations] == [1, 2]


def test_collection_matrix_is_built_from_majorities_across_depth() -> None:
    schema = make_schema(("A", "B", "C", "D"), depth=5)
    winners = repeat_tournament(schema.depth, four_type_moderate_tournament())
    result = analyze_session(make_responses(schema, winners), schema)
    assert result.binary_matrix == [
        [None, 0.0, 0.0, 0.0],
        [1.0, None, 0.0, 1.0],
        [1.0, 1.0, None, 0.0],
        [1.0, 0.0, 1.0, None],
    ]
    assert result.consistency.cyclic_triads == 1
    assert result.consistency.maximum_cyclic_triads == 2
    assert result.consistency.zeta == pytest.approx(0.5)
    assert result.status == "calculated"
    assert sum(item.percent for item in result.overall) == pytest.approx(100.0)


def test_incoming_workbook_selects_within_columns_then_uses_pair_majorities() -> None:
    schema, responses = incoming_selection_example()

    # Every workbook row compares items from exactly one common column.
    item_levels = {item.item_id: item.level_index for item in schema.items}
    assert all(
        item_levels[response.left_item_id]
        == item_levels[response.right_item_id]
        == response.level_index
        for response in responses
    )

    result = analyze_session(responses, schema)
    assert result.binary_matrix == [
        [None, 0.0, 0.0, 0.0],
        [1.0, None, 1.0, 1.0],
        [1.0, 0.0, None, 0.0],
        [1.0, 0.0, 1.0, None],
    ]
    assert result.consistency.zeta == 1.0
    ranked = sorted(result.overall, key=lambda score: score.percent, reverse=True)
    assert [score.type_name for score in ranked] == [
        "Архитектор", "Пилот", "Врач", "Инженер"
    ]


def test_fully_consistent_choice_session_converges_in_expected_order() -> None:
    schema = make_schema(("Doctor", "Engineer", "Builder", "Athlete"), depth=5)
    strict_order = {
        frozenset((1, 2)): 1,
        frozenset((1, 3)): 1,
        frozenset((1, 4)): 1,
        frozenset((2, 3)): 2,
        frozenset((2, 4)): 2,
        frozenset((3, 4)): 3,
    }
    result = analyze_session(
        make_responses(schema, repeat_tournament(schema.depth, strict_order)),
        schema,
    )
    assert result.status == "calculated"
    assert result.consistency.cyclic_triads == 0
    assert result.consistency.zeta == 1.0
    assert result.iteration.converged
    assert [item.type_name for item in result.overall] == [
        "Doctor",
        "Engineer",
        "Builder",
        "Athlete",
    ]
    scores = [item.percent for item in result.overall]
    assert scores == sorted(scores, reverse=True)
    assert sum(scores) == pytest.approx(100.0)


def test_low_consistency_returns_preferences_not_identified() -> None:
    schema = make_schema(("A", "B", "C"), depth=3)
    cycle = {
        frozenset((1, 2)): 1,
        frozenset((1, 3)): 3,
        frozenset((2, 3)): 2,
    }
    result = analyze_session(
        make_responses(schema, repeat_tournament(schema.depth, cycle)), schema
    )
    assert result.consistency.cyclic_triads == 1
    assert result.consistency.zeta == 0.0
    assert result.status == "preferences_not_identified"
    assert result.message == "Предпочтения не выявлены"
    assert result.overall is None
    assert result.iteration is None


def test_validation_total_time_is_sum_of_two_selected_per_pair() -> None:
    schema = make_schema(("A", "B", "C", "D"), depth=5)
    winners = repeat_tournament(schema.depth, four_type_moderate_tournament())
    aggregations = aggregate_pair_observations(
        make_responses(schema, winners, uniform_times(schema, 10.0)), schema
    )
    assert len(aggregations) == 6
    assert all(
        [observation.reaction_time_ms for observation in item.selected_observations]
        == [10.0, 10.0]
        for item in aggregations
    )
    assert compute_validation_total_time(aggregations) == pytest.approx(120.0)


def test_choice_only_ignores_times_but_time_mode_changes() -> None:
    schema = make_schema(("A", "B", "C", "D"), depth=5)
    winners = repeat_tournament(schema.depth, four_type_moderate_tournament())
    times_a = uniform_times(schema, 10.0)
    times_b = uniform_times(schema, 10.0)
    times_b[frozenset((1, 2))] = [100.0] * schema.depth

    first = compare_analysis_modes(make_responses(schema, winners, times_a), schema)
    second = compare_analysis_modes(make_responses(schema, winners, times_b), schema)

    assert [item.score for item in first.choice_only.overall] == pytest.approx(
        [item.score for item in second.choice_only.overall]
    )
    assert [item.score for item in first.choice_and_time.overall] != pytest.approx(
        [item.score for item in second.choice_and_time.overall]
    )


def test_source_v1_remains_distinct_from_experimental_symmetric_candidate() -> None:
    schema, responses = workbook_example()
    source = analyze_session(
        responses, schema, mode="choice_and_time", time_algorithm="source_v1"
    )
    symmetric = analyze_session(
        responses,
        schema,
        mode="choice_and_time",
        time_algorithm="symmetric_candidate_v2",
    )
    expected_source = [
        [None, 0.8834976648, 0.9831344058, 0.9469382460],
        [0.0958744162, None, 0.1037882719, 0.1087182148],
        [0.0535374503, 0.8897682062, None, 0.9251859540],
        [0.0629648850, 0.8922331777, 0.0958744162, None],
    ]
    expected_symmetric = [
        [None, 0.8834976648, 0.9831344058, 0.9469382460],
        [0.1165023352, None, 0.1037882719, 0.1087182148],
        [0.0168655942, 0.8962117281, None, 0.9251859540],
        [0.0530617540, 0.8912817852, 0.0748140460, None],
    ]
    np.testing.assert_allclose(
        np.asarray(source.time_weighted_matrix, dtype=float),
        np.asarray(expected_source, dtype=float),
        equal_nan=True,
    )
    np.testing.assert_allclose(
        np.asarray(symmetric.time_weighted_matrix, dtype=float),
        np.asarray(expected_symmetric, dtype=float),
        equal_nan=True,
    )

    source_percent = [item.percent for item in source.overall]
    symmetric_percent = [item.percent for item in symmetric.overall]
    difference = [
        candidate - baseline
        for baseline, candidate in zip(source_percent, symmetric_percent)
    ]
    assert source_percent == pytest.approx(
        [49.891037, 9.485929, 25.872138, 14.750897], abs=1e-6
    )
    assert symmetric_percent == pytest.approx(
        [49.983869, 10.485149, 24.962690, 14.568292], abs=1e-6
    )
    assert difference == pytest.approx(
        [0.092832, 0.999220, -0.909447, -0.182605], abs=1e-6
    )
    assert source.validation_total_time_ms == pytest.approx(23124.0)
    assert source.pair_time_matrix_ms == [
        [None, 2694.0, 390.0, 1227.0],
        [2217.0, None, 2400.0, 2514.0],
        [1238.0, 2549.0, None, 1730.0],
        [1456.0, 2492.0, 2217.0, None],
    ]
    assert source.iteration.iterations == 9
    assert source.iteration.initial_vector == [1.0, 1.0, 1.0, 1.0]
    assert source.iteration.raw_vectors[0] == pytest.approx(
        [2.8135703166, 0.3083809030, 1.8684916104, 1.0510724788]
    )
    # The cached XLSX result comes from a missing '+' in only the first row.
    assert source_percent != pytest.approx(
        [29.347238, 11.500782, 38.920332, 20.231648], abs=1e-6
    )

    print("\nsource_v1 P*:", source.time_weighted_matrix)
    print("source_v1 %:", source_percent)
    print("symmetric_candidate_v2 P*:", symmetric.time_weighted_matrix)
    print("symmetric_candidate_v2 %:", symmetric_percent)
    print("candidate - source, percentage points:", difference)


def test_photo_example_calculates_one_weight_as_row_scalar_product() -> None:
    matrix = np.array(
        [
            [np.nan, 0.5, 0.4, 0.3],
            [0.1, np.nan, 0.4, 0.3],
            [0.3, 0.2, np.nan, 0.3],
            [0.1, 0.3, 0.9, np.nan],
        ]
    )
    raw = calculate_next_raw_weights(matrix, [5.0, 3.0, 4.0, 2.0])
    assert raw[2] == pytest.approx(0.3 * 5 + 0.2 * 3 + 0.3 * 2)
    assert raw[2] == pytest.approx(2.7)


def test_iteration_uses_frozen_previous_vector_and_records_raw_values() -> None:
    matrix = np.array(
        [[np.nan, 1.0, 0.0], [0.0, np.nan, 1.0], [1.0, 0.0, np.nan]]
    )
    result = iterate_rank_weights(matrix)
    assert result.converged
    # The workbook compares the first normalized result with W(0)=[1,1,1].
    assert result.iterations == 2
    assert result.strategy is IterationStrategy.SELF_RETENTION_PROTOTYPE_V1
    assert result.initial_vector == [1.0, 1.0, 1.0]
    assert result.raw_vectors[0] == pytest.approx([2.0, 2.0, 2.0])
    assert result.normalized_vectors[-1] == pytest.approx([1 / 3, 1 / 3, 1 / 3])


def test_fully_consistent_matrix_converges_with_prototype_self_retention() -> None:
    matrix = np.array(
        [
            [np.nan, 1.0, 1.0, 1.0],
            [0.0, np.nan, 1.0, 1.0],
            [0.0, 0.0, np.nan, 1.0],
            [0.0, 0.0, 0.0, np.nan],
        ]
    )
    trace = iterate_rank_weights(matrix)
    assert trace.status == "converged"
    assert trace.iterations == 52
    assert trace.final_vector == pytest.approx(
        [0.9464285714, 0.0516233766, 0.0019119769, 0.0000360750],
        abs=1e-10,
    )
    assert trace.final_vector == sorted(trace.final_vector, reverse=True)


def test_literal_iteration_remains_available_as_zero_vector_diagnostic() -> None:
    matrix = np.array(
        [
            [np.nan, 1.0, 1.0, 1.0],
            [0.0, np.nan, 1.0, 1.0],
            [0.0, 0.0, np.nan, 1.0],
            [0.0, 0.0, 0.0, np.nan],
        ]
    )
    trace = iterate_rank_weights(matrix, strategy="literal_source_v1")
    assert trace.status == "zero_normalization_sum"
    assert trace.iterations == 4
    assert trace.final_vector == pytest.approx([1.0, 0.0, 0.0, 0.0])
    assert trace.raw_vectors[-1] == pytest.approx([0.0, 0.0, 0.0, 0.0])


def test_timeout_makes_pair_incomplete_and_is_not_imputed() -> None:
    schema = make_schema(("A", "B", "C"), depth=3)
    winners = repeat_tournament(
        schema.depth,
        {
            frozenset((1, 2)): 1,
            frozenset((1, 3)): 1,
            frozenset((2, 3)): 2,
        },
    )
    responses = make_responses(schema, winners)
    responses[0] = replace(
        responses[0],
        selected_item_id=None,
        selected_type_id=None,
        timed_out=True,
        status=ResponseStatus.TIMEOUT,
    )
    result = analyze_session(responses, schema)
    assert result.status == "insufficient_data"
    assert result.unresolved_pairs == 1
    assert result.binary_matrix is None
    assert result.pair_aggregations[0].status == "incomplete_pair"
    timeout_trace = result.pair_aggregations[0].observations[0]
    assert timeout_trace.left_item_id == "item-1-1"
    assert timeout_trace.right_item_id == "item-2-1"
    assert timeout_trace.selected_item_id is None
    assert timeout_trace.status is ResponseStatus.TIMEOUT
    assert timeout_trace.timed_out
    assert timeout_trace.role == "timeout"


def test_missing_response_makes_pair_incomplete() -> None:
    schema = make_schema(("A", "B"), depth=3)
    pair = frozenset((1, 2))
    responses = make_responses(schema, {pair: [1, 1, 2]})
    result = analyze_session(responses[:-1], schema)
    assert result.status == "insufficient_data"
    assert result.coverage == 0.0


def test_depth_one_supports_choice_but_not_two_observation_time_selection() -> None:
    schema = make_schema(("A", "B", "C", "D"), depth=1)
    winners = repeat_tournament(schema.depth, four_type_moderate_tournament())
    result = compare_analysis_modes(make_responses(schema, winners), schema)
    assert result.choice_only.status == "calculated"
    assert result.choice_and_time.status == "insufficient_time_data"


def test_width_two_uses_observed_choice_frequencies() -> None:
    schema = make_schema(("A", "B"), depth=5)
    pair = frozenset((1, 2))
    result = compare_analysis_modes(
        make_responses(schema, {pair: [1, 1, 1, 2, 2]}), schema
    )
    assert result.choice_only.status == "calculated_width_2_frequency"
    assert [item.percent for item in result.choice_only.overall] == [60.0, 40.0]
    assert result.choice_only.consistency.zeta is None
    assert result.choice_and_time.status == "calculated_width_2_frequency"
    assert [item.percent for item in result.choice_and_time.overall] == [60.0, 40.0]
    assert result.choice_and_time.time_weighted_matrix is not None


def test_empty_response_list_returns_insufficient_data() -> None:
    schema = make_schema(("A", "B", "C"), depth=3)
    result = analyze_session([], schema)
    assert result.status == "insufficient_data"
    assert result.overall is None
    assert result.coverage == 0.0


def test_even_depth_is_always_rejected() -> None:
    schema = make_schema(("A", "B", "C"), depth=4)
    with pytest.raises(AnalyticsValidationError, match="positive odd integer"):
        analyze_session([], schema)


def test_duplicate_pair_within_level_is_validation_error() -> None:
    schema = make_schema(("A", "B"), depth=3)
    pair = frozenset((1, 2))
    responses = make_responses(schema, {pair: [1, 1, 2]})
    duplicate = replace(responses[0], comparison_index=99)
    with pytest.raises(AnalyticsValidationError, match="only once"):
        analyze_session([*responses, duplicate], schema)


def test_cross_level_items_are_validation_error() -> None:
    schema = make_schema(("A", "B"), depth=3)
    pair = frozenset((1, 2))
    responses = make_responses(schema, {pair: [1, 1, 2]})
    responses[0] = replace(responses[0], right_item_id="item-2-2")
    with pytest.raises(AnalyticsValidationError, match="different level_index"):
        analyze_session(responses, schema)


@pytest.mark.parametrize("reaction_time", [0.0, -1.0, math.inf, math.nan])
def test_invalid_answer_time_is_validation_error(reaction_time: float) -> None:
    schema = make_schema(("A", "B"), depth=3)
    pair = frozenset((1, 2))
    responses = make_responses(schema, {pair: [1, 1, 2]})
    responses[0] = replace(responses[0], reaction_time_ms=reaction_time)
    with pytest.raises(AnalyticsValidationError, match="reaction_time_ms"):
        analyze_session(responses, schema)


def test_time_formula_uses_each_directed_cell_time() -> None:
    binary = np.array(
        [[np.nan, 1.0, 0.0], [0.0, np.nan, 1.0], [1.0, 0.0, np.nan]]
    )
    pair_times = np.array(
        [[np.nan, 10.0, 100.0], [15.0, np.nan, 20.0], [30.0, 25.0, np.nan]]
    )
    weighted = build_time_weighted_matrix(binary, pair_times, 200.0)
    assert weighted[0, 1] == pytest.approx(1 - 10 / 200)
    assert weighted[1, 0] == pytest.approx(15 / 200)
    assert weighted[0, 2] == pytest.approx(100 / 200)
    assert weighted[2, 0] == pytest.approx(1 - 30 / 200)


def test_max_iterations_is_a_diagnostic_status() -> None:
    matrix = np.array([[np.nan, 1.0], [0.2, np.nan]])
    result = iterate_rank_weights(matrix, epsilon=1e-12, max_iterations=2)
    assert result.status == "max_iterations_reached"
    assert result.iterations == 2


def test_result_is_json_serializable_and_versioned() -> None:
    schema = make_schema(("A", "B", "C", "D"), depth=5)
    winners = repeat_tournament(schema.depth, four_type_moderate_tournament())
    result = compare_analysis_modes(
        make_responses(schema, winners, uniform_times(schema)),
        schema,
        session_metadata=SessionMetadata("session-1", "collection-1", 20260819),
    )
    encoded = json.dumps(result.to_dict(), ensure_ascii=False, allow_nan=False)
    assert '"algorithm_version": "prisma-analytics/0.6.0-level-majority"' in encoded
    assert '"iteration_strategy": "self_retention_prototype_v1"' in encoded
    assert '"random_seed": 20260819' in encoded
    assert '"selected_fastest_majority"' in encoded


def test_consistency_of_source_five_by_five_example() -> None:
    matrix = np.array(
        [
            [np.nan, 0, 1, 1, 1],
            [1, np.nan, 1, 1, 0],
            [0, 0, np.nan, 0, 0],
            [0, 0, 1, np.nan, 1],
            [0, 1, 1, 0, np.nan],
        ],
        dtype=float,
    )
    result = calculate_consistency(matrix)
    assert result.cyclic_triads == 2
    assert result.maximum_cyclic_triads == 5
    assert result.zeta == pytest.approx(0.6)
    assert result.classification == "moderate"
