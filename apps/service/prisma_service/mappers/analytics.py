"""Pure mappings that keep FastAPI models outside the mathematical package."""

from prisma.analytics import (
    CollectionItem,
    CollectionSchema,
    PairResponse,
    ResponseStatus,
    SessionMetadata,
    StimulusType,
)

from ..models import (
    CollectionSchemaPayload,
    PairResponsePayload,
    SessionMetadataPayload,
)


def to_collection_schema(payload: CollectionSchemaPayload) -> CollectionSchema:
    return CollectionSchema(
        collection_id=payload.collection_id,
        depth=payload.depth,
        types=tuple(
            StimulusType(type_id=item.type_id, name=item.name)
            for item in payload.types
        ),
        items=tuple(
            CollectionItem(
                item_id=item.item_id,
                type_id=item.type_id,
                level_index=item.level_index,
            )
            for item in payload.items
        ),
    )


def to_pair_responses(payloads: list[PairResponsePayload]) -> list[PairResponse]:
    return [
        PairResponse(
            session_id=item.session_id,
            collection_id=item.collection_id,
            level_index=item.level_index,
            comparison_index=item.comparison_index,
            left_item_id=item.left_item_id,
            right_item_id=item.right_item_id,
            left_type_id=item.left_type_id,
            right_type_id=item.right_type_id,
            selected_item_id=item.selected_item_id,
            selected_type_id=item.selected_type_id,
            reaction_time_ms=item.reaction_time_ms,
            time_limit_ms=item.time_limit_ms,
            exceeded_time_limit=item.exceeded_time_limit,
            timed_out=item.timed_out,
            status=ResponseStatus(item.status),
        )
        for item in payloads
    ]


def to_session_metadata(
    payload: SessionMetadataPayload | None,
) -> SessionMetadata | None:
    if payload is None:
        return None
    return SessionMetadata(
        session_id=payload.session_id,
        collection_id=payload.collection_id,
        random_seed=payload.random_seed,
    )
