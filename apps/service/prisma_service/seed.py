"""Idempotent SQLite seed for the first collection-editor prototype."""

from html import escape
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from prisma.persistence.models import Collection, CollectionItem, CollectionType, StimulusType
from prisma.persistence.repositories import AccountRepository
from prisma.security import hash_password

from .config import COLLECTION_STORAGE_ROOT


SEED_COLLECTION_ID = "demo-professions"
SEED_TYPES = (
    ("Врач", "#315ca8"),
    ("Инженер", "#3b7c75"),
    ("Строитель", "#936637"),
    ("Спортсмен", "#7a4f91"),
)


def seed_database(session: Session) -> None:
    _seed_accounts(session)
    if session.scalar(select(func.count(Collection.id))):
        session.commit()
        return

    collection = Collection(
        id=SEED_COLLECTION_ID,
        name="Профессиональные предпочтения",
        width=len(SEED_TYPES),
        depth=5,
        is_active=True,
        time_mode="timeout_mark",
        time_limit_ms=5_000,
    )
    session.add(collection)
    session.flush()

    for row_index, (name, color) in enumerate(SEED_TYPES, start=1):
        stimulus_type = StimulusType(name=name)
        session.add(stimulus_type)
        session.flush()
        session.add(
            CollectionType(
                collection_id=collection.id,
                type_id=stimulus_type.id,
                row_index=row_index,
            )
        )
        for level_index in range(1, collection.depth + 1):
            relative_path = _write_seed_svg(
                collection.id, name, color, row_index, level_index
            )
            session.add(
                CollectionItem(
                    collection_id=collection.id,
                    type_id=stimulus_type.id,
                    level_index=level_index,
                    image_path=relative_path,
                )
            )
    session.commit()


def _seed_accounts(session: Session) -> None:
    """Create predictable local prototype accounts without storing plain passwords."""

    repository = AccountRepository(session)
    if repository.find_by_login("admin") is None:
        repository.create(
            login="admin", password_hash=hash_password("admin123"),
            last_name="Администратор", first_name="ПРИЗМА", patronymic=None,
            roles=("ADMIN", "USER"),
        )
    if repository.find_by_login("user") is None:
        repository.create(
            login="user", password_hash=hash_password("user1234"),
            last_name="Иванов", first_name="Иван", patronymic="Иванович",
            roles=("USER",),
        )


def _write_seed_svg(
    collection_id: str,
    type_name: str,
    color: str,
    row_index: int,
    level_index: int,
) -> str:
    directory = COLLECTION_STORAGE_ROOT / collection_id
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"seed-{row_index}-{level_index}.svg"
    path = directory / filename
    if not path.exists():
        label = escape(type_name)
        path.write_text(
            (
                '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="320" '
                'viewBox="0 0 480 320">'
                f'<rect width="480" height="320" fill="{color}"/>'
                '<rect x="20" y="20" width="440" height="280" rx="18" '
                'fill="white" fill-opacity="0.92"/>'
                f'<text x="240" y="150" text-anchor="middle" font-family="Segoe UI" '
                f'font-size="30" fill="{color}">{label}</text>'
                f'<text x="240" y="195" text-anchor="middle" font-family="Segoe UI" '
                f'font-size="18" fill="#667085">Изображение {level_index}</text>'
                '</svg>'
            ),
            encoding="utf-8",
        )
    return f"{collection_id}/{filename}"
