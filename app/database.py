"""Подключение к SQLite."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.config import DATABASE_PATH


@contextmanager
def get_connection(database_path: Path = DATABASE_PATH) -> Iterator[sqlite3.Connection]:
    """Открыть соединение с SQLite и включить контроль внешних ключей."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
