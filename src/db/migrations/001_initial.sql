CREATE TABLE IF NOT EXISTS collections (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    width INTEGER NOT NULL,
    depth INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0,
    time_mode TEXT NOT NULL,
    time_limit_ms INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stimulus_types (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS collection_types (
    id TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    type_id TEXT NOT NULL REFERENCES stimulus_types(id) ON DELETE RESTRICT,
    row_index INTEGER NOT NULL,
    UNIQUE(collection_id, row_index),
    UNIQUE(collection_id, type_id)
);

CREATE TABLE IF NOT EXISTS collection_items (
    id TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    type_id TEXT NOT NULL REFERENCES stimulus_types(id) ON DELETE RESTRICT,
    level_index INTEGER NOT NULL,
    image_path TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(collection_id, type_id, level_index)
);
