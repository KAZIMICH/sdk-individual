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

CREATE TABLE IF NOT EXISTS assistant_websites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0),
    target_url TEXT NOT NULL UNIQUE CHECK (target_url LIKE 'https://%'),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS assistant_command_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase TEXT NOT NULL CHECK (length(trim(phrase)) > 0),
    normalized_phrase TEXT NOT NULL UNIQUE CHECK (length(trim(normalized_phrase)) > 0),
    action_code TEXT NOT NULL CHECK (action_code IN ('create_document', 'open_mail', 'web_search', 'open_site')),
    website_id INTEGER REFERENCES assistant_websites(id) ON DELETE RESTRICT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    CHECK (
        (action_code = 'open_site' AND website_id IS NOT NULL)
        OR (action_code <> 'open_site' AND website_id IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS assistant_actions (
    action_code TEXT PRIMARY KEY CHECK (action_code IN ('create_document', 'open_mail', 'web_search', 'open_site')),
    target_url TEXT CHECK (target_url IS NULL OR target_url LIKE 'https://%'),
    requires_query INTEGER NOT NULL DEFAULT 0 CHECK (requires_query IN (0, 1)),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);
"""


def initialize_database(database_path: Path = DATABASE_PATH) -> None:
    """Создать все таблицы приложения, если они ещё не существуют."""
    with get_connection(database_path) as connection:
        connection.executescript(SCHEMA)
        _migrate_command_aliases_for_sites(connection)
        _migrate_actions_for_sites(connection)


def _migrate_command_aliases_for_sites(connection: object) -> None:
    """Расширить таблицу команд связью с сайтами без потери существующих записей."""
    schema_row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'assistant_command_aliases'"
    ).fetchone()
    if schema_row is None or (
        "open_site" in schema_row["sql"] and "website_id" in schema_row["sql"]
    ):
        return

    connection.executescript(
        """
        ALTER TABLE assistant_command_aliases RENAME TO assistant_command_aliases_legacy;

        CREATE TABLE assistant_command_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase TEXT NOT NULL CHECK (length(trim(phrase)) > 0),
            normalized_phrase TEXT NOT NULL UNIQUE CHECK (length(trim(normalized_phrase)) > 0),
            action_code TEXT NOT NULL CHECK (action_code IN ('create_document', 'open_mail', 'web_search', 'open_site')),
            website_id INTEGER REFERENCES assistant_websites(id) ON DELETE RESTRICT,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            CHECK (
                (action_code = 'open_site' AND website_id IS NOT NULL)
                OR (action_code <> 'open_site' AND website_id IS NULL)
            )
        );

        INSERT INTO assistant_command_aliases (id, phrase, normalized_phrase, action_code, website_id, is_active)
        SELECT id, phrase, normalized_phrase, action_code, NULL, is_active
        FROM assistant_command_aliases_legacy;

        DROP TABLE assistant_command_aliases_legacy;
        """
    )


def _migrate_actions_for_sites(connection: object) -> None:
    """Расширить список разрешённых действий без потери их настроек."""
    schema_row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'assistant_actions'"
    ).fetchone()
    if schema_row is None or (
        "open_site" in schema_row["sql"] and "requires_query" in schema_row["sql"]
    ):
        return

    connection.executescript(
        """
        ALTER TABLE assistant_actions RENAME TO assistant_actions_legacy;

        CREATE TABLE assistant_actions (
            action_code TEXT PRIMARY KEY CHECK (action_code IN ('create_document', 'open_mail', 'web_search', 'open_site')),
            target_url TEXT CHECK (target_url IS NULL OR target_url LIKE 'https://%'),
            requires_query INTEGER NOT NULL DEFAULT 0 CHECK (requires_query IN (0, 1)),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        );

        INSERT INTO assistant_actions (action_code, target_url, requires_query, is_active)
        SELECT action_code, target_url, 0, is_active
        FROM assistant_actions_legacy;

        DROP TABLE assistant_actions_legacy;
        """
    )
