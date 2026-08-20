CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    login TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS roles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL UNIQUE REFERENCES accounts(id) ON DELETE CASCADE,
    last_name TEXT NOT NULL,
    first_name TEXT NOT NULL,
    patronymic TEXT
);

CREATE TABLE IF NOT EXISTS account_roles (
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    role_id TEXT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY(account_id, role_id)
);

CREATE TABLE IF NOT EXISTS test_sessions (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    collection_id TEXT REFERENCES collections(id) ON DELETE SET NULL,
    collection_snapshot TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    time_mode TEXT NOT NULL,
    time_limit_ms INTEGER,
    random_seed TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comparison_responses (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES test_sessions(id) ON DELETE CASCADE,
    presentation_index INTEGER NOT NULL,
    level_index INTEGER NOT NULL,
    is_training INTEGER NOT NULL DEFAULT 0,
    left_item_id TEXT NOT NULL,
    right_item_id TEXT NOT NULL,
    left_type_id TEXT NOT NULL,
    right_type_id TEXT NOT NULL,
    selected_item_id TEXT,
    selected_type_id TEXT,
    reaction_time_ms REAL,
    exceeded_time_limit INTEGER NOT NULL DEFAULT 0,
    timed_out INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    shown_at TEXT,
    answered_at TEXT,
    UNIQUE(session_id, presentation_index)
);

CREATE TABLE IF NOT EXISTS analysis_results (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES test_sessions(id) ON DELETE CASCADE,
    analysis_mode TEXT NOT NULL,
    algorithm_version TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(session_id, analysis_mode)
);
