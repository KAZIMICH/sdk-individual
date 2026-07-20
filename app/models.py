"""SQL-схема таблиц приложения."""

from pathlib import Path

from app.config import DATABASE_PATH
from app.database import get_connection


SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0),
    director TEXT NOT NULL CHECK (length(trim(director)) > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_objects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    imo TEXT NOT NULL UNIQUE CHECK (length(trim(imo)) > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    object_id INTEGER NOT NULL REFERENCES project_objects(id) ON DELETE RESTRICT,
    subject TEXT NOT NULL CHECK (length(trim(subject)) > 0),
    amount_kopecks INTEGER NOT NULL CHECK (amount_kopecks > 0),
    lead_time_days INTEGER NOT NULL CHECK (lead_time_days > 0),
    validity_period_days INTEGER NOT NULL CHECK (validity_period_days > 0),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'generated', 'error')),
    file_path TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_work_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    comment TEXT,
    UNIQUE (document_id, position)
);
"""


def initialize_database(database_path: Path = DATABASE_PATH) -> None:
    """Создать все таблицы приложения, если они ещё не существуют."""
    with get_connection(database_path) as connection:
        connection.executescript(SCHEMA)
