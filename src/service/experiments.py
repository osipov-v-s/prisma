"""Pair schedule, autosave, session history, and analytics orchestration."""

from datetime import datetime, timezone
from itertools import combinations
import json
import random
import secrets
from uuid import uuid4

from src.core.models import Account
from src.db.database import get_db, transaction
from .analysis import analyze_stored_session
from .collections import get_collection, list_collections
from .snapshots import normalize_snapshot


class ExperimentError(ValueError):
    pass


def available_tests() -> list[dict]:
    return [{key: item[key] for key in ("id", "name", "width", "depth",
            "time_mode", "time_limit_ms")} for item in list_collections(True)]


def create_session(account_id: str, collection_id: str,
                   random_seed: str | None = None) -> dict:
    """Create only the main procedure; training can be added later as an option."""

    collection = get_collection(collection_id)
    if not collection["is_active"]:
        raise ExperimentError("Активная коллекция не найдена.")
    session_id = str(uuid4())
    seed = random_seed or str(secrets.randbits(63))
    snapshot = _snapshot(collection)
    schedule = _schedule(snapshot, seed)
    with transaction() as connection:
        connection.execute(
            """INSERT INTO test_sessions VALUES (?, ?, ?, ?, ?, NULL,
               'in_progress', ?, ?, ?)""",
            (session_id, account_id, collection_id, json.dumps(snapshot, ensure_ascii=False),
             _now(), collection["time_mode"], collection["time_limit_ms"], seed),
        )
        connection.executemany(
            """INSERT INTO comparison_responses
               (id, session_id, presentation_index, level_index, is_training,
                left_item_id, right_item_id, left_type_id, right_type_id,
                exceeded_time_limit, timed_out, status)
               VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, 0, 0, 'pending')""",
            [(str(uuid4()), session_id, item["presentation_index"], item["level_index"],
              item["left_item_id"], item["right_item_id"], item["left_type_id"],
              item["right_type_id"]) for item in schedule],
        )
    return get_session(session_id, account_id, False)


def list_sessions(account: Account) -> list[dict]:
    with get_db() as connection:
        sql = "SELECT id FROM test_sessions"
        params = ()
        if "ADMIN" not in account.roles:
            sql += " WHERE account_id = ?"
            params = (account.id,)
        sql += " ORDER BY started_at DESC"
        ids = [row["id"] for row in connection.execute(sql, params)]
    return [get_session(item, account.id, "ADMIN" in account.roles) for item in ids]


def get_session(session_id: str, account_id: str, is_admin: bool,
                include_trace: bool = False) -> dict:
    session = _authorized_session(session_id, account_id, is_admin)
    with get_db() as connection:
        comparisons = list(connection.execute(
            "SELECT * FROM comparison_responses WHERE session_id=? ORDER BY presentation_index",
            (session_id,),
        ))
        analysis = connection.execute(
            "SELECT result_json FROM analysis_results WHERE session_id=? AND analysis_mode='combined'",
            (session_id,),
        ).fetchone()
        profile = connection.execute(
            """SELECT p.last_name, p.first_name, p.patronymic FROM profiles p
               WHERE p.account_id=?""", (session["account_id"],)
        ).fetchone()
    snapshot = normalize_snapshot(json.loads(session["collection_snapshot"]))
    trace = [_comparison_dict(item, snapshot) for item in comparisons]
    next_item = next((item for item in trace if item["status"] == "pending" and
                      bool(item["is_training"]) == (session["status"] == "training")), None)
    return _session_dict(session, snapshot, profile, trace, next_item,
                         json.loads(analysis["result_json"]) if analysis else None,
                         include_trace)


def present_next(session_id: str, account_id: str) -> dict:
    session = _authorized_session(session_id, account_id, False)
    training = session["status"] == "training"
    with transaction() as connection:
        row = connection.execute(
            """SELECT id FROM comparison_responses WHERE session_id=? AND
               is_training=? AND status='pending' ORDER BY presentation_index LIMIT 1""",
            (session_id, int(training)),
        ).fetchone()
        if row:
            connection.execute(
                "UPDATE comparison_responses SET shown_at=COALESCE(shown_at, ?) WHERE id=?",
                (_now(), row["id"]),
            )
    return get_session(session_id, account_id, False)


def start_main(session_id: str, account_id: str) -> dict:
    """Compatibility only for unfinished sessions created by Desktop 1.0."""

    session = _authorized_session(session_id, account_id, False)
    if session["status"] not in {"training", "ready"}:
        raise ExperimentError("Основная процедура уже начата.")
    with transaction() as connection:
        connection.execute("UPDATE test_sessions SET status='in_progress' WHERE id=?",
                           (session_id,))
    return get_session(session_id, account_id, False)


def save_response(session_id: str, index: int, account_id: str, data: dict) -> dict:
    session = _authorized_session(session_id, account_id, False)
    row = _pending_comparison(session_id, index)
    selected = data.get("selected_item_id")
    timed_out = bool(data.get("timed_out"))
    _validate_response(session, row, selected, timed_out)
    selected_type = None
    if selected:
        selected_type = row["left_type_id"] if selected == row["left_item_id"] else row["right_type_id"]
    reaction = data.get("reaction_time_ms")
    exceeded = bool(session["time_limit_ms"] and reaction is not None
                    and reaction > session["time_limit_ms"])
    with transaction() as connection:
        connection.execute(
            """UPDATE comparison_responses SET selected_item_id=?, selected_type_id=?,
               reaction_time_ms=?, exceeded_time_limit=?, timed_out=?, status=?, answered_at=?
               WHERE id=?""",
            (selected, selected_type, reaction, int(exceeded), int(timed_out),
             "timeout" if timed_out else "answered", _now(), row["id"]),
        )
    _advance_or_finish(session_id)
    return get_session(session_id, account_id, False)


def _advance_or_finish(session_id: str) -> None:
    with get_db() as connection:
        session = connection.execute("SELECT status FROM test_sessions WHERE id=?", (session_id,)).fetchone()
        training_left = connection.execute("SELECT 1 FROM comparison_responses WHERE session_id=? AND is_training=1 AND status='pending'", (session_id,)).fetchone()
        main_left = connection.execute("SELECT 1 FROM comparison_responses WHERE session_id=? AND is_training=0 AND status='pending'", (session_id,)).fetchone()
    if session["status"] == "training" and not training_left:
        with transaction() as connection:
            connection.execute("UPDATE test_sessions SET status='ready' WHERE id=?", (session_id,))
    elif session["status"] == "in_progress" and not main_left:
        result = analyze_stored_session(session_id)
        with transaction() as connection:
            connection.execute("UPDATE test_sessions SET status='completed', finished_at=? WHERE id=?", (_now(), session_id))
            connection.execute(
                """INSERT OR REPLACE INTO analysis_results VALUES (?, ?, 'combined', ?, ?, ?)""",
                (str(uuid4()), session_id, result["algorithm_version"],
                 json.dumps(result, ensure_ascii=False), _now()),
            )


def _schedule(snapshot: dict, seed: str) -> list[dict]:
    """Build randomized pair blocks without ever mixing stimulus levels."""

    generator = random.Random(seed)
    slots = {(cell["type_id"], cell["level_index"]): cell
             for row in snapshot["rows"] for cell in row["cells"]}
    type_ids = [row["type_id"] for row in snapshot["rows"]]
    pairs = []
    for level in range(1, snapshot["depth"] + 1):
        level_pairs = []
        for first, second in combinations(type_ids, 2):
            left, right = (second, first) if generator.random() < .5 else (first, second)
            level_pairs.append({
                "level_index": level,
                "left_type_id": left,
                "right_type_id": right,
                "left_item_id": slots[(left, level)]["item_id"],
                "right_item_id": slots[(right, level)]["item_id"],
            })
        generator.shuffle(level_pairs)
        pairs.extend(level_pairs)
    return [{**item, "presentation_index": index} for index, item in enumerate(pairs, 1)]


def _snapshot(collection: dict) -> dict:
    rows = []
    for row in collection["rows"]:
        rows.append({"row_index": row["row_index"], "type_id": row["type_id"],
                     "type_name": row["type_name"],
                     "cells": [{**cell, "type_id": row["type_id"]} for cell in row["cells"]]})
    return {key: collection[key] for key in ("id", "name", "width", "depth",
            "time_mode", "time_limit_ms")} | {"rows": rows}


def _authorized_session(session_id: str, account_id: str, is_admin: bool):
    with get_db() as connection:
        row = connection.execute("SELECT * FROM test_sessions WHERE id=?", (session_id,)).fetchone()
    if row is None or (not is_admin and row["account_id"] != account_id):
        raise ExperimentError("Сессия не найдена или недоступна.")
    return row


def _pending_comparison(session_id: str, index: int):
    with get_db() as connection:
        row = connection.execute("SELECT * FROM comparison_responses WHERE session_id=? AND presentation_index=?", (session_id, index)).fetchone()
    if row is None or row["status"] != "pending":
        raise ExperimentError("Ответ на эту пару уже сохранён или пара не найдена.")
    return row


def _validate_response(session, row, selected: str | None, timed_out: bool) -> None:
    if timed_out and session["time_mode"] != "timeout_skip":
        raise ExperimentError("Автоматический пропуск разрешён только в timeout_skip.")
    if not timed_out and selected not in {row["left_item_id"], row["right_item_id"]}:
        raise ExperimentError("Выбранный стимул не входит в предъявленную пару.")


def _comparison_dict(row, snapshot: dict) -> dict:
    names = {item["type_id"]: item["type_name"] for item in snapshot["rows"]}
    paths = {cell["item_id"]: cell["image_path"] for item in snapshot["rows"] for cell in item["cells"]}
    return {"presentation_index": row["presentation_index"], "level_index": row["level_index"],
            "is_training": bool(row["is_training"]), "left_item_id": row["left_item_id"],
            "right_item_id": row["right_item_id"], "left_type_id": row["left_type_id"],
            "right_type_id": row["right_type_id"], "left_type_name": names[row["left_type_id"]],
            "right_type_name": names[row["right_type_id"]],
            "selected_type_name": names.get(row["selected_type_id"]),
            "left_image_url": f'prisma-media://image/{paths[row["left_item_id"]]}',
            "right_image_url": f'prisma-media://image/{paths[row["right_item_id"]]}',
            "selected_item_id": row["selected_item_id"], "selected_type_id": row["selected_type_id"],
            "reaction_time_ms": row["reaction_time_ms"],
            "exceeded_time_limit": bool(row["exceeded_time_limit"]), "timed_out": bool(row["timed_out"]),
            "status": row["status"], "shown_at": row["shown_at"], "answered_at": row["answered_at"]}


def _session_dict(session, snapshot, profile, trace, next_item, analysis, include_trace) -> dict:
    training = [item for item in trace if item["is_training"]]
    main = [item for item in trace if not item["is_training"]]
    full_name = " ".join(filter(None, (profile["last_name"], profile["first_name"], profile["patronymic"])))
    return {"id": session["id"], "account_id": session["account_id"], "user_name": full_name,
            "collection_id": session["collection_id"], "collection_name": snapshot["name"],
            "status": session["status"], "time_mode": session["time_mode"],
            "time_limit_ms": session["time_limit_ms"], "random_seed": session["random_seed"],
            "started_at": session["started_at"], "finished_at": session["finished_at"],
            "training_total": len(training), "training_completed": sum(i["status"] != "pending" for i in training),
            "main_total": len(main), "main_completed": sum(i["status"] != "pending" for i in main),
            "next_comparison": next_item, "comparisons": trace if include_trace else None,
            "analysis": analysis}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
