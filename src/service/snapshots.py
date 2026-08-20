"""Read both current snapshots and snapshots written by Desktop 1.0."""


def normalize_snapshot(snapshot: dict) -> dict:
    """Convert the former separate `items` list to row-owned cells in memory."""

    if all("cells" in row for row in snapshot.get("rows", [])):
        return snapshot
    items_by_type = {}
    for item in snapshot.get("items", []):
        items_by_type.setdefault(item["type_id"], []).append(item)
    rows = []
    for row in snapshot.get("rows", []):
        cells = [
            {"item_id": item["id"], "type_id": item["type_id"],
             "level_index": item["level_index"], "image_path": item["image_path"],
             "image_url": None}
            for item in sorted(items_by_type.get(row["type_id"], []),
                               key=lambda value: value["level_index"])
        ]
        rows.append({**row, "cells": cells})
    return {**snapshot, "rows": rows}
