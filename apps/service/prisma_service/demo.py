"""Small deterministic dataset used by the first UI vertical slice."""

from itertools import combinations

from .models import CompareAnalysisRequest


TYPE_NAMES = ("Врач", "Инженер", "Строитель", "Спортсмен")
PAIR_WINNERS = {
    (1, 2): 2,
    (1, 3): 3,
    (1, 4): 4,
    (2, 3): 3,
    (2, 4): 2,
    (3, 4): 4,
}


def make_demo_request() -> CompareAnalysisRequest:
    depth = 5
    collection_id = "demo-professions"
    session_id = "demo-session"
    types = [
        {"type_id": index, "name": name}
        for index, name in enumerate(TYPE_NAMES, start=1)
    ]
    items = [
        {
            "item_id": f"demo-{type_id}-{level}",
            "type_id": type_id,
            "level_index": level,
        }
        for level in range(1, depth + 1)
        for type_id in range(1, len(TYPE_NAMES) + 1)
    ]
    responses = []
    comparison_index = 1
    for level in range(1, depth + 1):
        for left, right in combinations(range(1, len(TYPE_NAMES) + 1), 2):
            winner = PAIR_WINNERS[(left, right)]
            responses.append(
                {
                    "session_id": session_id,
                    "collection_id": collection_id,
                    "level_index": level,
                    "comparison_index": comparison_index,
                    "left_item_id": f"demo-{left}-{level}",
                    "right_item_id": f"demo-{right}-{level}",
                    "left_type_id": left,
                    "right_type_id": right,
                    "selected_item_id": f"demo-{winner}-{level}",
                    "selected_type_id": winner,
                    "reaction_time_ms": 550 + 70 * comparison_index,
                    "time_limit_ms": 5_000,
                }
            )
            comparison_index += 1
    return CompareAnalysisRequest.model_validate(
        {
            "collection": {
                "collection_id": collection_id,
                "depth": depth,
                "types": types,
                "items": items,
            },
            "responses": responses,
            "session": {
                "session_id": session_id,
                "collection_id": collection_id,
                "random_seed": 20260819,
            },
        }
    )
