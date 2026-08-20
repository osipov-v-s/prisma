"""Trusted seed images and validated user image storage."""

import base64
from html import escape
from io import BytesIO
from pathlib import Path
import re
from uuid import uuid4
from xml.etree import ElementTree

from PIL import Image, UnidentifiedImageError

from src.db.database import database_path


MAX_IMAGE_SIZE = 10 * 1024 * 1024
EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png",
              "image/webp": ".webp", "image/gif": ".gif",
              "image/svg+xml": ".svg"}
FORBIDDEN_SVG_ELEMENTS = {"script", "foreignobject", "iframe", "object", "embed"}
UNSAFE_SVG_TEXT = ("javascript:", "@import")
SVG_URL_PATTERN = re.compile(r"url\(\s*['\"]?([^'\")\s]+)", re.IGNORECASE)


def storage_root() -> Path:
    return database_path().parent / "collections"


def store_image(collection_id: str, content_type: str, content_base64: str) -> str:
    """Validate a raster or safe standalone SVG under an internal UUID name."""

    extension = EXTENSIONS.get(content_type)
    if extension is None:
        raise ValueError("Поддерживаются JPEG, PNG, WebP, GIF и SVG.")
    content = base64.b64decode(content_base64, validate=True)
    if not content or len(content) > MAX_IMAGE_SIZE:
        raise ValueError("Изображение пусто или превышает 10 МБ.")
    content = (
        _validated_svg(content)
        if content_type == "image/svg+xml"
        else _validated_raster(content)
    )
    directory = storage_root() / collection_id
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4()}{extension}"
    (directory / filename).write_bytes(content)
    return f"{collection_id}/{filename}"


def _validated_raster(content: bytes) -> bytes:
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("Файл не является корректным изображением.") from error
    return content


def _validated_svg(content: bytes) -> bytes:
    """Reject active/external SVG content and return normalized XML bytes."""

    lowered = content.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise ValueError("SVG не должен содержать DTD или XML-сущности.")
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        raise ValueError("Файл не является корректным SVG.") from error
    if _local_name(root.tag) != "svg":
        raise ValueError("Корневой элемент SVG должен называться svg.")

    for element in root.iter():
        tag = _local_name(element.tag)
        if tag in FORBIDDEN_SVG_ELEMENTS:
            raise ValueError(f"SVG содержит запрещённый элемент: {tag}.")
        _validate_svg_attributes(element)
        if tag == "style" and _unsafe_svg_value(element.text or ""):
            raise ValueError("SVG-стили не должны загружать внешние ресурсы.")
    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


def _validate_svg_attributes(element: ElementTree.Element) -> None:
    for raw_name, raw_value in element.attrib.items():
        name = _local_name(raw_name)
        value = raw_value.strip().lower()
        if name.startswith("on"):
            raise ValueError("Обработчики событий в SVG запрещены.")
        if name in {"href", "src"} and value and not value.startswith("#"):
            raise ValueError("SVG не должен ссылаться на внешние ресурсы.")
        if _unsafe_svg_value(value):
            raise ValueError("SVG содержит небезопасную ссылку или стиль.")


def _local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1].casefold()


def _unsafe_svg_value(value: str) -> bool:
    normalized = value.casefold()
    if any(marker in normalized for marker in UNSAFE_SVG_TEXT):
        return True
    return any(not match.group(1).startswith("#") for match in SVG_URL_PATTERN.finditer(value))


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
