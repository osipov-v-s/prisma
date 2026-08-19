"""Application workflow for training, pair presentation, autosave, and analysis."""

from datetime import datetime, timezone
from itertools import combinations
import random
import secrets

from sqlalchemy.orm import Session

from prisma.analytics import (
    CollectionItem as AnalyticsItem, CollectionSchema, PairResponse,
    ResponseStatus, SessionMetadata, StimulusType, compare_analysis_modes,
)
from prisma.persistence.models import Collection, ComparisonResponse, TestSession
from prisma.persistence.repositories import CollectionRepository, ExperimentRepository


class ExperimentError(ValueError):
    pass


def list_available_collections(database: Session) -> list[dict]:
    return [
        {"id": item.id, "name": item.name, "width": item.width, "depth": item.depth,
         "time_mode": item.time_mode, "time_limit_ms": item.time_limit_ms}
        for item in CollectionRepository(database).list() if item.is_active
    ]


def create_test_session(database: Session, account_id: str, collection_id: str,
                        random_seed: str | None = None) -> dict:
    collection = CollectionRepository(database).get(collection_id)
    if collection is None or not collection.is_active:
        raise ExperimentError("Активная коллекция не найдена.")
    seed = random_seed or str(secrets.randbits(63))
    snapshot = _collection_snapshot(collection)
    test_session = TestSession(
        account_id=account_id, collection_id=collection.id,
        collection_snapshot=snapshot, time_mode=collection.time_mode,
        time_limit_ms=collection.time_limit_ms, random_seed=seed, status="training",
    )
    schedule = _build_schedule(snapshot, seed)
    test_session.comparisons = [ComparisonResponse(**item) for item in schedule]
    ExperimentRepository(database).add(test_session)
    database.commit()
    return serialize_session(ExperimentRepository(database).get(test_session.id))


def get_test_session(database: Session, session_id: str, account_id: str,
                     is_admin: bool, include_trace: bool = False) -> dict:
    test_session = _authorized_session(database, session_id, account_id, is_admin)
    return serialize_session(test_session, include_trace=include_trace)


def list_test_sessions(database: Session, account_id: str, is_admin: bool) -> list[dict]:
    repository = ExperimentRepository(database)
    sessions = repository.list_all() if is_admin else repository.list_for_account(account_id)
    return [serialize_session(item) for item in sessions]


def start_main_test(database: Session, session_id: str, account_id: str) -> dict:
    test_session = _authorized_session(database, session_id, account_id, False)
    training = [item for item in test_session.comparisons if item.is_training]
    if any(item.status == "pending" for item in training):
        raise ExperimentError("Сначала завершите тренировочные сравнения.")
    if test_session.status not in {"training", "ready"}:
        raise ExperimentError("Основная процедура уже начата или завершена.")
    test_session.status = "in_progress"
    database.commit()
    return serialize_session(ExperimentRepository(database).get(test_session.id))


def present_next(database: Session, session_id: str, account_id: str) -> dict:
    test_session = _authorized_session(database, session_id, account_id, False)
    comparison = _next_comparison(test_session)
    if comparison and comparison.shown_at is None:
        comparison.shown_at = datetime.now(timezone.utc)
        database.commit()
    return serialize_session(ExperimentRepository(database).get(test_session.id))


def save_response(database: Session, session_id: str, presentation_index: int,
                  account_id: str, selected_item_id: str | None,
                  reaction_time_ms: float | None, timed_out: bool) -> dict:
    test_session = _authorized_session(database, session_id, account_id, False)
    comparison = next((item for item in test_session.comparisons
                       if item.presentation_index == presentation_index), None)
    if comparison is None:
        raise ExperimentError("Предъявление не найдено.")
    if comparison.status != "pending":
        raise ExperimentError("Ответ на эту пару уже сохранён.")
    expected = _next_comparison(test_session)
    if expected is None or expected.id != comparison.id:
        raise ExperimentError("Ответы должны сохраняться в порядке предъявления.")

    if timed_out:
        if test_session.time_mode != "timeout_skip":
            raise ExperimentError("Автоматический пропуск допустим только в timeout_skip.")
        selected_item_id = None
        comparison.status = "timeout"
        comparison.timed_out = True
    else:
        if selected_item_id not in {comparison.left_item_id, comparison.right_item_id}:
            raise ExperimentError("Выбранный стимул не входит в предъявленную пару.")
        comparison.selected_item_id = selected_item_id
        comparison.selected_type_id = (
            comparison.left_type_id if selected_item_id == comparison.left_item_id
            else comparison.right_type_id
        )
        comparison.status = "answered"
    comparison.reaction_time_ms = reaction_time_ms
    comparison.exceeded_time_limit = bool(
        test_session.time_limit_ms is not None and reaction_time_ms is not None
        and reaction_time_ms > test_session.time_limit_ms
    )
    comparison.answered_at = datetime.now(timezone.utc)

    if comparison.is_training:
        if not any(item.is_training and item.status == "pending" for item in test_session.comparisons):
            test_session.status = "ready"
    elif not any(not item.is_training and item.status == "pending" for item in test_session.comparisons):
        _finish_and_analyze(database, test_session)
    database.commit()
    return serialize_session(ExperimentRepository(database).get(test_session.id))


def _finish_and_analyze(database: Session, test_session: TestSession) -> None:
    test_session.finished_at = datetime.now(timezone.utc)
    test_session.status = "completed"
    result = _analyze(test_session)
    ExperimentRepository(database).replace_analysis(test_session, result)


def _analyze(test_session: TestSession) -> dict:
    snapshot = test_session.collection_snapshot
    schema = CollectionSchema(
        collection_id=snapshot["id"], depth=snapshot["depth"],
        types=tuple(StimulusType(type_id=row["type_id"], name=row["type_name"])
                    for row in snapshot["rows"]),
        items=tuple(AnalyticsItem(item_id=item["id"], type_id=item["type_id"],
                                  level_index=item["level_index"])
                    for item in snapshot["items"]),
    )
    responses = [
        PairResponse(
            session_id=test_session.id, collection_id=snapshot["id"],
            level_index=item.level_index, comparison_index=item.presentation_index,
            left_item_id=item.left_item_id, right_item_id=item.right_item_id,
            left_type_id=item.left_type_id, right_type_id=item.right_type_id,
            selected_item_id=item.selected_item_id, selected_type_id=item.selected_type_id,
            reaction_time_ms=item.reaction_time_ms, time_limit_ms=test_session.time_limit_ms,
            exceeded_time_limit=item.exceeded_time_limit, timed_out=item.timed_out,
            status=ResponseStatus.TIMEOUT if item.timed_out else ResponseStatus.ANSWERED,
        )
        for item in test_session.comparisons if not item.is_training
    ]
    return compare_analysis_modes(
        responses, schema, session_metadata=SessionMetadata(
            session_id=test_session.id, collection_id=snapshot["id"],
            random_seed=test_session.random_seed,
        )
    ).to_dict()


def _collection_snapshot(collection: Collection) -> dict:
    return {
        "id": collection.id, "name": collection.name, "width": collection.width,
        "depth": collection.depth, "time_mode": collection.time_mode,
        "time_limit_ms": collection.time_limit_ms,
        "rows": [{"row_index": row.row_index, "type_id": row.type_id,
                  "type_name": row.stimulus_type.name} for row in collection.type_rows],
        "items": [{"id": item.id, "type_id": item.type_id,
                   "level_index": item.level_index, "image_path": item.image_path}
                  for item in collection.items],
    }


def _build_schedule(snapshot: dict, seed: str) -> list[dict]:
    generator = random.Random(seed)
    by_slot = {(item["type_id"], item["level_index"]): item for item in snapshot["items"]}
    type_ids = [row["type_id"] for row in sorted(snapshot["rows"], key=lambda row: row["row_index"])]
    main: list[dict] = []
    for level_index in range(1, snapshot["depth"] + 1):
        for first_type, second_type in combinations(type_ids, 2):
            left_type, right_type = (first_type, second_type)
            if generator.random() < 0.5:
                left_type, right_type = right_type, left_type
            main.append({"level_index": level_index, "left_item_id": by_slot[(left_type, level_index)]["id"],
                         "right_item_id": by_slot[(right_type, level_index)]["id"],
                         "left_type_id": left_type, "right_type_id": right_type})
    generator.shuffle(main)
    training = [dict(item) for item in main[:min(3, len(main))]]
    schedule = []
    for index, item in enumerate(training + main, start=1):
        schedule.append({**item, "presentation_index": index,
                         "is_training": index <= len(training), "status": "pending"})
    return schedule


def _authorized_session(database: Session, session_id: str, account_id: str,
                        is_admin: bool) -> TestSession:
    test_session = ExperimentRepository(database).get(session_id)
    if test_session is None:
        raise ExperimentError("Сессия не найдена.")
    if not is_admin and test_session.account_id != account_id:
        raise ExperimentError("Нет доступа к этой сессии.")
    return test_session


def _next_comparison(test_session: TestSession) -> ComparisonResponse | None:
    training_phase = test_session.status in {"training", "ready"}
    if test_session.status == "ready":
        return None
    return next((item for item in test_session.comparisons
                 if item.is_training == training_phase and item.status == "pending"), None)


def serialize_session(test_session: TestSession, include_trace: bool = False) -> dict:
    snapshot = test_session.collection_snapshot
    images = {item["id"]: f'/media/{item["image_path"]}' for item in snapshot["items"]}
    type_names = {row["type_id"]: row["type_name"] for row in snapshot["rows"]}
    comparisons = [
        _serialize_comparison(item, images, type_names)
        for item in test_session.comparisons
    ]
    training = [item for item in test_session.comparisons if item.is_training]
    main = [item for item in test_session.comparisons if not item.is_training]
    next_item = _next_comparison(test_session)
    analysis = next((item.result_json for item in test_session.analysis_results
                     if item.analysis_mode == "combined"), None)
    return {
        "id": test_session.id, "account_id": test_session.account_id,
        "user_name": test_session.account.profile.full_name,
        "collection_id": test_session.collection_id, "collection_name": snapshot["name"],
        "status": test_session.status, "time_mode": test_session.time_mode,
        "time_limit_ms": test_session.time_limit_ms, "random_seed": test_session.random_seed,
        "started_at": test_session.started_at.isoformat(),
        "finished_at": test_session.finished_at.isoformat() if test_session.finished_at else None,
        "training_total": len(training), "training_completed": sum(item.status != "pending" for item in training),
        "main_total": len(main), "main_completed": sum(item.status != "pending" for item in main),
        "next_comparison": (
            _serialize_comparison(next_item, images, type_names) if next_item else None
        ),
        "comparisons": comparisons if include_trace else None, "analysis": analysis,
    }


def _serialize_comparison(
    item: ComparisonResponse,
    images: dict[str, str],
    type_names: dict[str, str],
) -> dict:
    return {
        "presentation_index": item.presentation_index, "level_index": item.level_index,
        "is_training": item.is_training, "left_item_id": item.left_item_id,
        "right_item_id": item.right_item_id, "left_type_id": item.left_type_id,
        "right_type_id": item.right_type_id,
        "left_type_name": type_names[item.left_type_id],
        "right_type_name": type_names[item.right_type_id],
        "selected_type_name": type_names.get(item.selected_type_id) if item.selected_type_id else None,
        "left_image_url": images[item.left_item_id],
        "right_image_url": images[item.right_item_id], "selected_item_id": item.selected_item_id,
        "selected_type_id": item.selected_type_id, "reaction_time_ms": item.reaction_time_ms,
        "exceeded_time_limit": item.exceeded_time_limit, "timed_out": item.timed_out,
        "status": item.status, "shown_at": item.shown_at.isoformat() if item.shown_at else None,
        "answered_at": item.answered_at.isoformat() if item.answered_at else None,
    }
