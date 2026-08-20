"""Collection editor business rules implemented with direct SQLite queries."""

from datetime import datetime, timezone
from uuid import uuid4

from src.db.database import get_db, transaction
from .images import store_image, write_seed_svg


SEED_ID = "demo-professions"
SEED_TYPES = (("Врач", "#315ca8"), ("Инженер", "#3b7c75"),
              ("Строитель", "#936637"), ("Спортсмен", "#7a4f91"))


class CollectionError(ValueError):
    pass


def list_collections(active_only: bool = False) -> list[dict]:
    sql = "SELECT id FROM collections"
    if active_only:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY updated_at DESC"
    with get_db() as connection:
        identifiers = [row["id"] for row in connection.execute(sql)]
    return [get_collection(identifier) for identifier in identifiers]


def get_collection(collection_id: str) -> dict:
    with get_db() as connection:
        collection = connection.execute(
            "SELECT * FROM collections WHERE id = ?", (collection_id,)
        ).fetchone()
        if collection is None:
            raise CollectionError("Коллекция не найдена.")
        rows = list(connection.execute(
            """SELECT ct.row_index, st.id AS type_id, st.name AS type_name
               FROM collection_types ct JOIN stimulus_types st ON st.id = ct.type_id
               WHERE ct.collection_id = ? ORDER BY ct.row_index""", (collection_id,)
        ))
        items = list(connection.execute(
            "SELECT * FROM collection_items WHERE collection_id = ?", (collection_id,)
        ))
    return _serialize(collection, rows, items)


def create_collection(data: dict) -> dict:
    _validate_draft(data)
    collection_id = data.get("_id") or str(uuid4())
    now = _now()
    with transaction() as connection:
        connection.execute(
            """INSERT INTO collections VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)""",
            (collection_id, data["name"].strip(), data["width"], data["depth"],
             data["time_mode"], _time_limit(data), now, now),
        )
        _replace_rows(connection, collection_id, data, {})
    return get_collection(collection_id)


def update_collection(collection_id: str, data: dict) -> dict:
    _validate_draft(data)
    current = get_collection(collection_id)
    preserved = {(row["type_name"].casefold(), cell["level_index"]): cell["image_path"]
                 for row in current["rows"] for cell in row["cells"] if cell["image_path"]}
    with transaction() as connection:
        connection.execute(
            """UPDATE collections SET name=?, width=?, depth=?, is_active=0,
               time_mode=?, time_limit_ms=?, updated_at=? WHERE id=?""",
            (data["name"].strip(), data["width"], data["depth"], data["time_mode"],
             _time_limit(data), _now(), collection_id),
        )
        connection.execute("DELETE FROM collection_items WHERE collection_id=?", (collection_id,))
        connection.execute("DELETE FROM collection_types WHERE collection_id=?", (collection_id,))
        _replace_rows(connection, collection_id, data, preserved)
    return get_collection(collection_id)


def set_active(collection_id: str, active: bool) -> dict:
    collection = get_collection(collection_id)
    if active and collection["activation"]["errors"]:
        raise CollectionError("; ".join(collection["activation"]["errors"]))
    with transaction() as connection:
        connection.execute("UPDATE collections SET is_active=?, updated_at=? WHERE id=?",
                           (int(active), _now(), collection_id))
    return get_collection(collection_id)


def assign_image(collection_id: str, row_index: int, level_index: int,
                 content_type: str, content_base64: str) -> dict:
    collection = get_collection(collection_id)
    if not 1 <= row_index <= collection["width"] or not 1 <= level_index <= collection["depth"]:
        raise CollectionError("Ячейка находится за пределами коллекции.")
    row = next((item for item in collection["rows"] if item["row_index"] == row_index), None)
    if not row or not row["type_id"]:
        raise CollectionError("Перед загрузкой изображения задайте тип строки.")
    path = store_image(collection_id, content_type, content_base64)
    with transaction() as connection:
        connection.execute(
            """UPDATE collection_items SET image_path=?
               WHERE collection_id=? AND type_id=? AND level_index=?""",
            (path, collection_id, row["type_id"], level_index),
        )
        connection.execute("UPDATE collections SET is_active=0, updated_at=? WHERE id=?",
                           (_now(), collection_id))
    return get_collection(collection_id)


def seed_collection() -> None:
    with get_db() as connection:
        if connection.execute("SELECT 1 FROM collections LIMIT 1").fetchone():
            return
    data = {"name": "Профессиональные предпочтения", "width": 4, "depth": 5,
            "time_mode": "timeout_mark", "time_limit_ms": 5000,
            "_id": SEED_ID,
            "rows": [{"row_index": index, "type_name": name}
                     for index, (name, _) in enumerate(SEED_TYPES, 1)]}
    created = create_collection(data)
    with transaction() as connection:
        for row, (_, color) in zip(created["rows"], SEED_TYPES, strict=True):
            for level in range(1, 6):
                path = write_seed_svg(SEED_ID, row["type_name"], color, row["row_index"], level)
                connection.execute(
                    "UPDATE collection_items SET image_path=? WHERE collection_id=? AND type_id=? AND level_index=?",
                    (path, created["id"], row["type_id"], level),
                )
        connection.execute("UPDATE collections SET is_active=1 WHERE id=?", (created["id"],))


def _replace_rows(connection, collection_id: str, data: dict, preserved: dict) -> None:
    for row in data.get("rows", []):
        name = row.get("type_name", "").strip()
        if not name:
            continue
        type_id = _get_or_create_type(connection, name)
        connection.execute("INSERT INTO collection_types VALUES (?, ?, ?, ?)",
                           (str(uuid4()), collection_id, type_id, row["row_index"]))
        for level in range(1, data["depth"] + 1):
            connection.execute("INSERT INTO collection_items VALUES (?, ?, ?, ?, ?, ?)",
                               (str(uuid4()), collection_id, type_id, level,
                                preserved.get((name.casefold(), level)), _now()))


def _get_or_create_type(connection, name: str) -> str:
    existing = next((row for row in connection.execute("SELECT id, name FROM stimulus_types")
                     if row["name"].casefold() == name.casefold()), None)
    if existing:
        return existing["id"]
    type_id = str(uuid4())
    connection.execute("INSERT INTO stimulus_types VALUES (?, ?)", (type_id, name))
    return type_id


def _validate_draft(data: dict) -> None:
    if not str(data.get("name", "")).strip():
        raise CollectionError("Укажите название коллекции.")
    if not 2 <= int(data.get("width", 0)) <= 20:
        raise CollectionError("Ширина должна быть от 2 до 20.")
    depth = int(data.get("depth", 0))
    if not 1 <= depth <= 99 or depth % 2 == 0:
        raise CollectionError("Количество изображений каждого типа должно быть нечётным.")
    indices = [row["row_index"] for row in data.get("rows", [])]
    if len(indices) != len(set(indices)) or any(not 1 <= item <= data["width"] for item in indices):
        raise CollectionError("Некорректные номера строк.")
    if data["time_mode"] not in {"timeout_skip", "timeout_mark", "no_limit"}:
        raise CollectionError("Неизвестный режим времени.")
    if data["time_mode"] != "no_limit" and not data.get("time_limit_ms"):
        raise CollectionError("Для режима с ограничением укажите время.")


def _activation_errors(collection: dict) -> list[str]:
    errors = []
    if collection["depth"] < 1 or collection["depth"] % 2 == 0:
        errors.append("Для активации глубина должна быть положительной и нечётной.")
    typed_rows = [row for row in collection["rows"] if row["type_id"]]
    if len(typed_rows) != collection["width"]:
        errors.append("Не заданы типы для всех строк.")
    if any(not cell["image_path"] for row in typed_rows for cell in row["cells"]):
        errors.append("Не загружены изображения во все ячейки.")
    return errors


def _serialize(collection, type_rows, items) -> dict:
    by_index = {row["row_index"]: row for row in type_rows}
    by_slot = {(item["type_id"], item["level_index"]): item for item in items}
    rows = []
    for index in range(1, collection["width"] + 1):
        type_row = by_index.get(index)
        cells = []
        for level in range(1, collection["depth"] + 1):
            item = by_slot.get((type_row["type_id"], level)) if type_row else None
            path = item["image_path"] if item else None
            cells.append({"item_id": item["id"] if item else None, "level_index": level,
                          "image_path": path, "image_url": f"prisma-media://image/{path}" if path else None})
        rows.append({"row_index": index, "type_id": type_row["type_id"] if type_row else None,
                     "type_name": type_row["type_name"] if type_row else "", "cells": cells})
    result = {key: collection[key] for key in ("id", "name", "width", "depth", "time_mode", "time_limit_ms", "created_at", "updated_at")}
    result.update({"is_active": bool(collection["is_active"]), "rows": rows})
    errors = _activation_errors(result)
    result["activation"] = {"can_activate": not errors, "errors": errors}
    return result


def _time_limit(data: dict) -> int | None:
    return None if data["time_mode"] == "no_limit" else data.get("time_limit_ms")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
