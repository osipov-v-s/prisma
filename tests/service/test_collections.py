"""Collection draft, image grid, and activation rules without HTTP fixtures."""

import base64

import pytest

from src.service import collections


ONE_PIXEL_PNG = base64.b64encode(base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)).decode()


def draft() -> dict:
    return {"name": "Новая коллекция", "width": 2, "depth": 5,
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


def test_edit_preserves_images_for_unchanged_types(desktop_db) -> None:
    created = collections.create_collection(draft())
    created = collections.assign_image(created["id"], 1, 1, "image/png", ONE_PIXEL_PNG)
    path = created["rows"][0]["cells"][0]["image_path"]
    updated = collections.update_collection(created["id"], draft())
    assert updated["rows"][0]["cells"][0]["image_path"] == path
