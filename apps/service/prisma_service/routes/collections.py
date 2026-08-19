"""HTTP endpoints of the collection editor."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from prisma.persistence.database import get_database_session

from ..auth import require_admin
from ..models import CollectionWrite
from ..services import (
    CollectionEditorError,
    CollectionNotFoundError,
    activate_collection,
    assign_image,
    create_collection,
    deactivate_collection,
    get_collection,
    list_collections,
    update_collection,
)
from ..storage import ImageStorageError, store_collection_image


router = APIRouter(
    prefix="/collections", tags=["collections"],
    dependencies=[Depends(require_admin)],
)


@router.get("")
def list_all(session: Session = Depends(get_database_session)) -> list[dict]:
    return list_collections(session)


@router.post("", status_code=201)
def create(
    payload: CollectionWrite,
    session: Session = Depends(get_database_session),
) -> dict:
    return _translate_errors(lambda: create_collection(session, payload))


@router.get("/{collection_id}")
def get_one(
    collection_id: str,
    session: Session = Depends(get_database_session),
) -> dict:
    return _translate_errors(lambda: get_collection(session, collection_id))


@router.put("/{collection_id}")
def update(
    collection_id: str,
    payload: CollectionWrite,
    session: Session = Depends(get_database_session),
) -> dict:
    return _translate_errors(
        lambda: update_collection(session, collection_id, payload)
    )


@router.post("/{collection_id}/activate")
def activate(
    collection_id: str,
    session: Session = Depends(get_database_session),
) -> dict:
    return _translate_errors(lambda: activate_collection(session, collection_id))


@router.post("/{collection_id}/deactivate")
def deactivate(
    collection_id: str,
    session: Session = Depends(get_database_session),
) -> dict:
    return _translate_errors(lambda: deactivate_collection(session, collection_id))


@router.post("/{collection_id}/rows/{row_index}/levels/{level_index}/image")
async def upload_image(
    collection_id: str,
    row_index: int,
    level_index: int,
    image: UploadFile = File(...),
    session: Session = Depends(get_database_session),
) -> dict:
    try:
        content = await image.read()
        image_path = store_collection_image(collection_id, image.content_type, content)
        return assign_image(
            session, collection_id, row_index, level_index, image_path
        )
    except ImageStorageError as error:
        raise HTTPException(status_code=422, detail=[str(error)]) from error
    except CollectionNotFoundError as error:
        raise HTTPException(status_code=404, detail="Коллекция не найдена.") from error
    except CollectionEditorError as error:
        raise HTTPException(status_code=422, detail=error.errors) from error


def _translate_errors(operation):
    try:
        return operation()
    except CollectionNotFoundError as error:
        raise HTTPException(status_code=404, detail="Коллекция не найдена.") from error
    except CollectionEditorError as error:
        raise HTTPException(status_code=422, detail=error.errors) from error
