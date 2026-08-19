"""Replaceable filesystem storage adapter for uploaded collection images."""

from pathlib import Path
from io import BytesIO
import uuid

from PIL import Image, UnidentifiedImageError

from .config import COLLECTION_STORAGE_ROOT


MAX_IMAGE_SIZE = 10 * 1024 * 1024
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class ImageStorageError(ValueError):
    pass


def prepare_storage() -> None:
    COLLECTION_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)


def store_collection_image(
    collection_id: str,
    content_type: str | None,
    content: bytes,
) -> str:
    extension = CONTENT_TYPE_EXTENSIONS.get(content_type or "")
    if extension is None:
        raise ImageStorageError("Поддерживаются JPEG, PNG, WebP и GIF.")
    if not content:
        raise ImageStorageError("Загруженный файл пуст.")
    if len(content) > MAX_IMAGE_SIZE:
        raise ImageStorageError("Размер изображения не должен превышать 10 МБ.")
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as error:
        raise ImageStorageError("Файл не является корректным растровым изображением.") from error

    directory = COLLECTION_STORAGE_ROOT / collection_id
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}{extension}"
    (directory / filename).write_bytes(content)
    return f"{collection_id}/{filename}"
