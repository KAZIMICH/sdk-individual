"""Создание SQLite-базы приложения и тестовое заполнение справочников."""

from pathlib import Path

from app.config import DATABASE_PATH
from app.database import get_connection
from app.models import initialize_database


SEED_CUSTOMERS = (
    ("ООО Альфа", "Иванов Иван Иванович"),
    ("ООО Бета", "Петров Петр Петрович"),
    ("ООО Гамма", "Сидоров Сергей Сергеевич"),
    ("ООО Дельта", "Кузнецов Алексей Викторович"),
    ("ООО Омега", "Смирнова Анна Павловна"),
)

SEED_PROJECT_OBJECTS = (
    ("Тестовое судно Север", "1234567"),
    ("Тестовое судно Восток", "2345678"),
    ("Тестовое судно Юг", "3456789"),
    ("Тестовое судно Запад", "4567890"),
    ("Тестовое судно Полярный", "5678901"),
    ("Тестовое судно Океан", "6789012"),
    ("Тестовое судно Волна", "7890123"),
    ("Тестовое судно Горизонт", "8901234"),
)

SEED_ASSISTANT_COMMAND_ALIASES = (
    ("Создай КП", "создайкп", "create_document"),
    ("Сделай КП", "сделайкп", "create_document"),
    ("Новое предложение", "новоепредложение", "create_document"),
    ("Создай коммерческое предложение", "создайкоммерческоепредложение", "create_document"),
    ("Сделай коммерческое предложение", "сделайкоммерческоепредложение", "create_document"),
    ("Создай капе", "создайкапе", "create_document"),
    ("Сделай капе", "сделайкапе", "create_document"),
    ("Открой почту", "откройпочту", "open_mail"),
    ("Открой почтовый ящик", "откройпочтовыйящик", "open_mail"),
    ("Открой электронную почту", "откройэлектроннуюпочту", "open_mail"),
    ("Найди", "найди", "web_search"),
    ("Найти", "найти", "web_search"),
    ("Поиск", "поиск", "web_search"),
)

SEED_ASSISTANT_WEBSITES = (
    ("Российский морской регистр судоходства", "https://rs-class.org/"),
    ("Adomat Marine", "https://adomatmarine.ru/"),
    ("Российское классификационное общество (РКО)", "https://rfclass.ru/"),
    ("Fleetphoto", "https://fleetphoto.ru/"),
)

SEED_ASSISTANT_SITE_COMMAND_ALIASES = (
    (
        "Российский морской регистр судоходства",
        "Открой Российский морской регистр судоходства",
        "откройроссийскийморскойрегистрсудоходства",
    ),
    ("Российский морской регистр судоходства", "Открой РС", "откройрс"),
    ("Российский морской регистр судоходства", "Открой РМРС", "откройрмрс"),
    ("Adomat Marine", "Открой Adomat Marine", "откройadomatmarine"),
    (
        "Российское классификационное общество (РКО)",
        "Открой РКО",
        "откройрко",
    ),
    ("Fleetphoto", "Открой Fleetphoto", "откройfleetphoto"),
)

SEED_ASSISTANT_ACTIONS = (
    ("create_document", None, 0),
    ("open_mail", "https://e.mail.ru/", 0),
    ("web_search", "https://yandex.ru/search/?text=", 1),
    ("open_site", None, 0),
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
        connection.executemany(
            """
            INSERT INTO assistant_websites (name, target_url)
            VALUES (?, ?)
            ON CONFLICT(target_url) DO UPDATE SET name = excluded.name
            """,
            SEED_ASSISTANT_WEBSITES,
        )
        connection.executemany(
            """
            INSERT INTO assistant_command_aliases (phrase, normalized_phrase, action_code)
            VALUES (?, ?, ?)
            ON CONFLICT(normalized_phrase) DO NOTHING
            """,
            SEED_ASSISTANT_COMMAND_ALIASES,
        )
        connection.execute(
            """
            DELETE FROM assistant_command_aliases
            WHERE action_code = 'open_site' AND normalized_phrase = 'откройрусскийрегистр'
            """
        )
        website_ids = {
            row["name"]: row["id"]
            for row in connection.execute(
                "SELECT id, name FROM assistant_websites"
            )
        }
        connection.executemany(
            """
            INSERT INTO assistant_command_aliases (
                phrase, normalized_phrase, action_code, website_id
            ) VALUES (?, ?, 'open_site', ?)
            ON CONFLICT(normalized_phrase) DO NOTHING
            """,
            [
                (phrase, normalized_phrase, website_ids[website_name])
                for website_name, phrase, normalized_phrase in SEED_ASSISTANT_SITE_COMMAND_ALIASES
            ],
        )
        connection.executemany(
            """
            INSERT INTO assistant_actions (action_code, target_url, requires_query)
            VALUES (?, ?, ?)
            ON CONFLICT(action_code) DO NOTHING
            """,
            SEED_ASSISTANT_ACTIONS,
        )


def main() -> None:
    initialize_database()
    seed_reference_data()
    print("SQLite database initialized with test reference data.")


if __name__ == "__main__":
    main()
