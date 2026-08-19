"""Readable business rules for collection drafts and activation."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from prisma.persistence.models import Collection, CollectionItem, CollectionType
from prisma.persistence.repositories import CollectionRepository

from ..models import CollectionWrite


class CollectionNotFoundError(LookupError):
    pass


class CollectionEditorError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def list_collections(session: Session) -> list[dict]:
    return [_serialize_collection(item) for item in CollectionRepository(session).list()]


def get_collection(session: Session, collection_id: str) -> dict:
    collection = _require_collection(session, collection_id)
    return _serialize_collection(collection)


def create_collection(session: Session, payload: CollectionWrite) -> dict:
    collection = Collection(
        name=payload.name.strip(),
        width=payload.width,
        depth=payload.depth,
        time_mode=payload.time_mode,
        time_limit_ms=payload.time_limit_ms,
        is_active=False,
    )
    repository = CollectionRepository(session)
    repository.add(collection)
    session.flush()
    _apply_editor_payload(session, repository, collection, payload)
    session.commit()
    return _reload_and_serialize(session, collection.id)


def update_collection(
    session: Session, collection_id: str, payload: CollectionWrite
) -> dict:
    collection = _require_collection(session, collection_id)
    repository = CollectionRepository(session)
    _apply_editor_payload(session, repository, collection, payload)
    # A changed active collection must pass validation again before publication.
    collection.is_active = False
    session.commit()
    return _reload_and_serialize(session, collection.id)


def activate_collection(session: Session, collection_id: str) -> dict:
    collection = _require_collection(session, collection_id)
    errors = _activation_errors(collection)
    if errors:
        raise CollectionEditorError(errors)
    collection.is_active = True
    collection.updated_at = datetime.now(timezone.utc)
    session.commit()
    return _reload_and_serialize(session, collection.id)


def deactivate_collection(session: Session, collection_id: str) -> dict:
    collection = _require_collection(session, collection_id)
    collection.is_active = False
    collection.updated_at = datetime.now(timezone.utc)
    session.commit()
    return _reload_and_serialize(session, collection.id)


def assign_image(
    session: Session,
    collection_id: str,
    row_index: int,
    level_index: int,
    image_path: str,
) -> dict:
    collection = _require_collection(session, collection_id)
    if row_index < 1 or row_index > collection.width:
        raise CollectionEditorError(["Строка находится за пределами коллекции."])
    if level_index < 1 or level_index > collection.depth:
        raise CollectionEditorError(["Уровень находится за пределами глубины."])
    type_row = next(
        (item for item in collection.type_rows if item.row_index == row_index), None
    )
    if type_row is None:
        raise CollectionEditorError(["Перед загрузкой изображения задайте тип строки."])
    item = next(
        (
            candidate
            for candidate in collection.items
            if candidate.type_id == type_row.type_id
            and candidate.level_index == level_index
        ),
        None,
    )
    if item is None:
        item = CollectionItem(
            collection_id=collection.id,
            type_id=type_row.type_id,
            level_index=level_index,
        )
        session.add(item)
    item.image_path = image_path
    collection.is_active = False
    collection.updated_at = datetime.now(timezone.utc)
    session.commit()
    return _reload_and_serialize(session, collection.id)


def _apply_editor_payload(
    session: Session,
    repository: CollectionRepository,
    collection: Collection,
    payload: CollectionWrite,
) -> None:
    normalized_names = [row.type_name.strip() for row in payload.rows if row.type_name.strip()]
    if len({name.casefold() for name in normalized_names}) != len(normalized_names):
        raise CollectionEditorError(["Типы строк внутри коллекции не должны повторяться."])

    collection.name = payload.name.strip()
    collection.width = payload.width
    collection.depth = payload.depth
    collection.time_mode = payload.time_mode
    collection.time_limit_ms = (
        None if payload.time_mode == "no_limit" else payload.time_limit_ms
    )
    collection.updated_at = datetime.now(timezone.utc)

    requested_rows = {row.row_index: row.type_name.strip() for row in payload.rows}
    existing_rows = {row.row_index: row for row in list(collection.type_rows)}

    for row_index, existing in existing_rows.items():
        requested_name = requested_rows.get(row_index, "")
        if row_index > payload.width or not requested_name:
            repository.delete_items_for_type(collection.id, existing.type_id)
            session.delete(existing)

    session.flush()
    existing_rows = {row.row_index: row for row in collection.type_rows if row in session}

    for row_index in range(1, payload.width + 1):
        requested_name = requested_rows.get(row_index, "")
        if not requested_name:
            continue
        stimulus_type = repository.get_or_create_type(requested_name)
        existing = existing_rows.get(row_index)
        if existing is None:
            existing = CollectionType(
                collection_id=collection.id,
                type_id=stimulus_type.id,
                row_index=row_index,
            )
            session.add(existing)
        elif existing.type_id != stimulus_type.id:
            repository.delete_items_for_type(collection.id, existing.type_id)
            existing.type_id = stimulus_type.id

        _synchronize_items(session, collection, stimulus_type.id, payload.depth)

    session.flush()


def _synchronize_items(
    session: Session, collection: Collection, type_id: str, depth: int
) -> None:
    items = list(
        session.scalars(
            select(CollectionItem).where(
                CollectionItem.collection_id == collection.id,
                CollectionItem.type_id == type_id,
            )
        )
    )
    by_level = {item.level_index: item for item in items}
    for item in items:
        if item.level_index > depth:
            session.delete(item)
    for level_index in range(1, depth + 1):
        if level_index not in by_level:
            session.add(
                CollectionItem(
                    collection_id=collection.id,
                    type_id=type_id,
                    level_index=level_index,
                )
            )


def _activation_errors(collection: Collection) -> list[str]:
    errors: list[str] = []
    if collection.width < 2:
        errors.append("Необходимо минимум два типа.")
    if collection.depth < 5 or collection.depth % 2 == 0:
        errors.append("Для активации глубина должна быть нечётной и не меньше пяти.")
    if len(collection.type_rows) != collection.width:
        errors.append("Не заданы типы для всех строк.")
    type_ids = [row.type_id for row in collection.type_rows]
    if len(type_ids) != len(set(type_ids)):
        errors.append("Типы строк не должны повторяться.")
    expected_items = collection.width * collection.depth
    filled_items = sum(bool(item.image_path) for item in collection.items)
    if len(collection.items) != expected_items or filled_items != expected_items:
        errors.append("Не загружены изображения во все ячейки.")
    if collection.time_mode != "no_limit" and not collection.time_limit_ms:
        errors.append("Не задан лимит времени.")
    return errors


def _require_collection(session: Session, collection_id: str) -> Collection:
    collection = CollectionRepository(session).get(collection_id)
    if collection is None:
        raise CollectionNotFoundError(collection_id)
    return collection


def _reload_and_serialize(session: Session, collection_id: str) -> dict:
    session.expire_all()
    return _serialize_collection(_require_collection(session, collection_id))


def _serialize_collection(collection: Collection) -> dict:
    rows_by_index = {row.row_index: row for row in collection.type_rows}
    items_by_slot = {
        (item.type_id, item.level_index): item for item in collection.items
    }
    rows = []
    for row_index in range(1, collection.width + 1):
        type_row = rows_by_index.get(row_index)
        cells = []
        for level_index in range(1, collection.depth + 1):
            item = (
                items_by_slot.get((type_row.type_id, level_index))
                if type_row is not None
                else None
            )
            cells.append(
                {
                    "item_id": item.id if item is not None else None,
                    "level_index": level_index,
                    "image_path": item.image_path if item is not None else None,
                    "image_url": (
                        f"/media/{item.image_path}"
                        if item is not None and item.image_path
                        else None
                    ),
                }
            )
        rows.append(
            {
                "row_index": row_index,
                "type_id": type_row.type_id if type_row is not None else None,
                "type_name": (
                    type_row.stimulus_type.name if type_row is not None else ""
                ),
                "cells": cells,
            }
        )
    errors = _activation_errors(collection)
    return {
        "id": collection.id,
        "name": collection.name,
        "width": collection.width,
        "depth": collection.depth,
        "is_active": collection.is_active,
        "time_mode": collection.time_mode,
        "time_limit_ms": collection.time_limit_ms,
        "created_at": collection.created_at.isoformat(),
        "updated_at": collection.updated_at.isoformat(),
        "rows": rows,
        "activation": {"can_activate": not errors, "errors": errors},
    }
