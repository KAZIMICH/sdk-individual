"""Создание SQLite-базы приложения и тестовое заполнение справочников."""

from pathlib import Path

from app.config import DATABASE_PATH
from app.database import get_connection
from app.models import initialize_database


SEED_CUSTOMERS = (
    ("ООО Альфа", "Иванов Иван Иванович"),
    ("ООО Бета", "Петров Петр Петрович"),
)

SEED_PROJECT_OBJECTS = (
    ("Тестовое судно Север", "1234567"),
    ("Тестовое судно Восток", "2345678"),
    ("Тестовое судно Юг", "3456789"),
)


def seed_reference_data(database_path: Path = DATABASE_PATH) -> None:
    """Добавить вымышленные справочные данные без создания дубликатов."""
    with get_connection(database_path) as connection:
        connection.executemany(
            """
            INSERT INTO customers (name, director)
            VALUES (?, ?)
            ON CONFLICT(name) DO NOTHING
            """,
            SEED_CUSTOMERS,
        )
        connection.executemany(
            """
            INSERT INTO project_objects (name, imo)
            VALUES (?, ?)
            ON CONFLICT(imo) DO NOTHING
            """,
            SEED_PROJECT_OBJECTS,
        )


def main() -> None:
    initialize_database()
    seed_reference_data()
    print("SQLite database initialized with test reference data.")


if __name__ == "__main__":
    main()
