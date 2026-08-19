"""Database operations for collections without HTTP concerns."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Collection, CollectionItem, CollectionType, StimulusType


class CollectionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Collection]:
        statement = (
            select(Collection)
            .options(
                selectinload(Collection.type_rows).selectinload(
                    CollectionType.stimulus_type
                ),
                selectinload(Collection.items),
            )
            .order_by(Collection.updated_at.desc())
        )
        return list(self.session.scalars(statement).all())

    def get(self, collection_id: str) -> Collection | None:
        statement = (
            select(Collection)
            .where(Collection.id == collection_id)
            .options(
                selectinload(Collection.type_rows).selectinload(
                    CollectionType.stimulus_type
                ),
                selectinload(Collection.items),
            )
        )
        return self.session.scalar(statement)

    def find_type(self, name: str) -> StimulusType | None:
        exact = self.session.scalar(
            select(StimulusType).where(StimulusType.name == name)
        )
        if exact is not None:
            return exact
        # SQLite lower() handles ASCII only. Python casefold keeps the editor
        # correct for Cyrillic names and behaves the same with PostgreSQL.
        expected = name.casefold()
        return next(
            (
                item
                for item in self.session.scalars(select(StimulusType))
                if item.name.casefold() == expected
            ),
            None,
        )

    def get_or_create_type(self, name: str) -> StimulusType:
        existing = self.find_type(name)
        if existing is not None:
            return existing
        created = StimulusType(name=name)
        self.session.add(created)
        self.session.flush()
        return created

    def add(self, collection: Collection) -> None:
        self.session.add(collection)

    def delete_items_for_type(self, collection_id: str, type_id: str) -> None:
        for item in list(
            self.session.scalars(
                select(CollectionItem).where(
                    CollectionItem.collection_id == collection_id,
                    CollectionItem.type_id == type_id,
                )
            )
        ):
            self.session.delete(item)
