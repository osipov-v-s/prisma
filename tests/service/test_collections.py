"""Collection draft, image grid, and activation rules without HTTP fixtures."""

import base64

import pytest

from src.service import collections, images


ONE_PIXEL_PNG = base64.b64encode(base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)).decode()
SAFE_SVG = base64.b64encode(
    b'<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20">'
    b'<defs><linearGradient id="g"><stop stop-color="#315ca8"/></linearGradient></defs>'
    b'<rect width="20" height="20" fill="url(#g)"/></svg>'
).decode()
SCRIPT_SVG = base64.b64encode(
    b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
).decode()


def draft(depth: int = 5) -> dict:
    return {"name": "Новая коллекция", "width": 2, "depth": depth,
            "time_mode": "timeout_mark", "time_limit_ms": 5000,
            "rows": [{"row_index": 1, "type_name": "A"},
                     {"row_index": 2, "type_name": "B"}]}


def test_even_depth_is_rejected(desktop_db) -> None:
    data = draft()
    data["depth"] = 4
    with pytest.raises(collections.CollectionError, match="нечётным"):
        collections.create_collection(data)


def test_complete_grid_can_be_activated(desktop_db) -> None:
    created = collections.create_collection(draft())
    assert not created["activation"]["can_activate"]
    for row_index in (1, 2):
        for level_index in range(1, 6):
            created = collections.assign_image(
                created["id"], row_index, level_index, "image/png", ONE_PIXEL_PNG
            )
    activated = collections.set_active(created["id"], True)
    assert activated["is_active"]
    assert activated["activation"]["can_activate"]


def test_depth_one_can_be_activated(desktop_db) -> None:
    created = collections.create_collection(draft(depth=1))
    for row_index in (1, 2):
        created = collections.assign_image(
            created["id"], row_index, 1, "image/png", ONE_PIXEL_PNG
        )

    activated = collections.set_active(created["id"], True)

    assert activated["is_active"]
    assert activated["depth"] == 1


def test_safe_svg_can_be_uploaded(desktop_db) -> None:
    created = collections.create_collection(draft(depth=1))

    updated = collections.assign_image(
        created["id"], 1, 1, "image/svg+xml", SAFE_SVG
    )

    relative_path = updated["rows"][0]["cells"][0]["image_path"]
    assert relative_path.endswith(".svg")
    assert (images.storage_root() / relative_path).read_bytes().startswith(b"<?xml")


def test_active_content_in_svg_is_rejected(desktop_db) -> None:
    created = collections.create_collection(draft(depth=1))

    with pytest.raises(ValueError, match="запрещённый элемент"):
        collections.assign_image(
            created["id"], 1, 1, "image/svg+xml", SCRIPT_SVG
        )


def test_edit_preserves_images_for_unchanged_types(desktop_db) -> None:
    created = collections.create_collection(draft())
    created = collections.assign_image(created["id"], 1, 1, "image/png", ONE_PIXEL_PNG)
    path = created["rows"][0]["cells"][0]["image_path"]
    updated = collections.update_collection(created["id"], draft())
    assert updated["rows"][0]["cells"][0]["image_path"] == path
