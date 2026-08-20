"""Translate stored Desktop rows into the unchanged scientific kernel contracts."""

import json

from prisma.analytics import (
    CollectionItem,
    CollectionSchema,
    PairResponse,
    ResponseStatus,
    SessionMetadata,
    StimulusType,
    compare_analysis_modes,
)
from src.db.database import get_db
from .snapshots import normalize_snapshot


def analyze_stored_session(session_id: str) -> dict:
    """Run both approved modes from the persisted snapshot and main responses."""

    with get_db() as connection:
        session = connection.execute(
            "SELECT * FROM test_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        rows = list(connection.execute(
            """SELECT * FROM comparison_responses
               WHERE session_id = ? AND is_training = 0 ORDER BY presentation_index""",
            (session_id,),
        ))
    snapshot = normalize_snapshot(json.loads(session["collection_snapshot"]))
    schema = _schema(snapshot)
    responses = [_response(session, row, snapshot["id"]) for row in rows]
    metadata = SessionMetadata(session_id=session_id, collection_id=snapshot["id"],
                               random_seed=session["random_seed"])
    return compare_analysis_modes(
        responses, schema, session_metadata=metadata
    ).to_dict()


def _schema(snapshot: dict) -> CollectionSchema:
    items = [cell for row in snapshot["rows"] for cell in row["cells"]]
    return CollectionSchema(
        collection_id=snapshot["id"],
        depth=snapshot["depth"],
        types=tuple(
            StimulusType(type_id=row["type_id"], name=row["type_name"])
            for row in snapshot["rows"]
        ),
        items=tuple(
            CollectionItem(item_id=item["item_id"], type_id=item["type_id"],
                           level_index=item["level_index"])
            for item in items
        ),
    )


def _response(session, row, collection_id: str) -> PairResponse:
    return PairResponse(
        session_id=session["id"], collection_id=collection_id,
        level_index=row["level_index"], comparison_index=row["presentation_index"],
        left_item_id=row["left_item_id"], right_item_id=row["right_item_id"],
        left_type_id=row["left_type_id"], right_type_id=row["right_type_id"],
        selected_item_id=row["selected_item_id"], selected_type_id=row["selected_type_id"],
        reaction_time_ms=row["reaction_time_ms"], time_limit_ms=session["time_limit_ms"],
        exceeded_time_limit=bool(row["exceeded_time_limit"]),
        timed_out=bool(row["timed_out"]),
        status=ResponseStatus.TIMEOUT if row["timed_out"] else ResponseStatus.ANSWERED,
    )
