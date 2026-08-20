"""Trusted seed images and validated user image storage."""

import base64
from html import escape
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from src.db.database import database_path


MAX_IMAGE_SIZE = 10 * 1024 * 1024
EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png",
              "image/webp": ".webp", "image/gif": ".gif"}


def storage_root() -> Path:
    return database_path().parent / "collections"


def store_image(collection_id: str, content_type: str, content_base64: str) -> str:
    """Validate a raster image and store it under an internal UUID name."""

    extension = EXTENSIONS.get(content_type)
    if extension is None:
        raise ValueError("Поддерживаются JPEG, PNG, WebP и GIF.")
    content = base64.b64decode(content_base64, validate=True)
    if not content or len(content) > MAX_IMAGE_SIZE:
        raise ValueError("Изображение пусто или превышает 10 МБ.")
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("Файл не является корректным изображением.") from error
    directory = storage_root() / collection_id
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4()}{extension}"
    (directory / filename).write_bytes(content)
    return f"{collection_id}/{filename}"


def write_seed_svg(collection_id: str, type_name: str, color: str,
                   row_index: int, level_index: int) -> str:
    """Generate clearly marked trusted placeholders for the bundled demo."""

    directory = storage_root() / collection_id
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"seed-{row_index}-{level_index}.svg"
    path = directory / filename
    if not path.exists():
        label = escape(type_name)
        path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="320">'
            f'<rect width="480" height="320" fill="{color}"/>'
            '<rect x="20" y="20" width="440" height="280" rx="18" fill="white" fill-opacity=".92"/>'
            f'<text x="240" y="150" text-anchor="middle" font-family="Segoe UI" font-size="30" fill="{color}">{label}</text>'
            f'<text x="240" y="195" text-anchor="middle" font-family="Segoe UI" font-size="18" fill="#667085">Изображение {level_index}</text>'
            '</svg>', encoding="utf-8",
        )
    return f"{collection_id}/{filename}"
