"""Проверки начального заполнения SQLite."""

import tempfile
import unittest
from pathlib import Path

from app.database import get_connection
from app.models import initialize_database
from scripts.init_db import (
    SEED_ASSISTANT_ACTIONS,
    SEED_ASSISTANT_COMMAND_ALIASES,
    SEED_ASSISTANT_SITE_COMMAND_ALIASES,
    SEED_ASSISTANT_WEBSITES,
    SEED_CUSTOMERS,
    SEED_PROJECT_OBJECTS,
    seed_reference_data,
)


class SeedDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "test.db"
        initialize_database(self.database_path)

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_adds_all_test_reference_records(self) -> None:
        seed_reference_data(self.database_path)

        with get_connection(self.database_path) as connection:
            customer_count = connection.execute(
                "SELECT COUNT(*) AS count FROM customers"
            ).fetchone()["count"]
            object_count = connection.execute(
                "SELECT COUNT(*) AS count FROM project_objects"
            ).fetchone()["count"]
            command_alias_count = connection.execute(
                "SELECT COUNT(*) AS count FROM assistant_command_aliases"
            ).fetchone()["count"]
            action_count = connection.execute(
                "SELECT COUNT(*) AS count FROM assistant_actions"
            ).fetchone()["count"]
            website_count = connection.execute(
                "SELECT COUNT(*) AS count FROM assistant_websites"
            ).fetchone()["count"]

        self.assertEqual(customer_count, len(SEED_CUSTOMERS))
        self.assertEqual(object_count, len(SEED_PROJECT_OBJECTS))
        self.assertEqual(
            command_alias_count,
            len(SEED_ASSISTANT_COMMAND_ALIASES) + len(SEED_ASSISTANT_SITE_COMMAND_ALIASES),
        )
        self.assertEqual(action_count, len(SEED_ASSISTANT_ACTIONS))
        self.assertEqual(website_count, len(SEED_ASSISTANT_WEBSITES))

        with get_connection(self.database_path) as connection:
            search_action = connection.execute(
                "SELECT target_url, requires_query FROM assistant_actions WHERE action_code = 'web_search'"
            ).fetchone()

        self.assertEqual(
            (search_action["target_url"], search_action["requires_query"]),
            ("https://yandex.ru/search/?text=", 1),
        )

    def test_adds_mail_command_aliases(self) -> None:
        seed_reference_data(self.database_path)

        with get_connection(self.database_path) as connection:
            aliases = {
                row["normalized_phrase"]
                for row in connection.execute(
                    """
                    SELECT normalized_phrase
                    FROM assistant_command_aliases
                    WHERE action_code = 'open_mail'
                    """
                )
            }

        self.assertEqual(
            aliases,
            {"откройпочту", "откройпочтовыйящик", "откройэлектроннуюпочту"},
        )

    def test_adds_search_command_aliases(self) -> None:
        seed_reference_data(self.database_path)

        with get_connection(self.database_path) as connection:
            aliases = {
                row["normalized_phrase"]
                for row in connection.execute(
                    """
                    SELECT normalized_phrase
                    FROM assistant_command_aliases
                    WHERE action_code = 'web_search'
                    """
                )
            }

        self.assertEqual(aliases, {"найди", "найти", "поиск"})

    def test_adds_site_commands_with_whitelisted_urls(self) -> None:
        seed_reference_data(self.database_path)

        with get_connection(self.database_path) as connection:
            site_commands = {
                (row["normalized_phrase"], row["name"], row["target_url"])
                for row in connection.execute(
                    """
                    SELECT aliases.normalized_phrase, websites.name, websites.target_url
                    FROM assistant_command_aliases AS aliases
                    JOIN assistant_websites AS websites ON websites.id = aliases.website_id
                    WHERE aliases.action_code = 'open_site'
                    """
                )
            }

        self.assertEqual(
            site_commands,
            {
                ("откройроссийскийморскойрегистрсудоходства", "Российский морской регистр судоходства", "https://rs-class.org/"),
                ("откройрс", "Российский морской регистр судоходства", "https://rs-class.org/"),
                ("откройрмрс", "Российский морской регистр судоходства", "https://rs-class.org/"),
                ("откройadomatmarine", "Adomat Marine", "https://adomatmarine.ru/"),
                (
                    "откройрко",
                    "Российское классификационное общество (РКО)",
                    "https://rfclass.ru/",
                ),
                ("откройfleetphoto", "Fleetphoto", "https://fleetphoto.ru/"),
            },
        )

    def test_corrects_outdated_rko_name_and_command(self) -> None:
        with get_connection(self.database_path) as connection:
            website_id = connection.execute(
                "INSERT INTO assistant_websites (name, target_url) VALUES (?, ?)",
                ("Outdated name", "https://rfclass.ru/"),
            ).lastrowid
            connection.execute(
                """
                INSERT INTO assistant_command_aliases (
                    phrase, normalized_phrase, action_code, website_id
                ) VALUES (?, ?, ?, ?)
                """,
                ("Outdated command", "откройрусскийрегистр", "open_site", website_id),
            )

        seed_reference_data(self.database_path)

        with get_connection(self.database_path) as connection:
            website = connection.execute(
                "SELECT name FROM assistant_websites WHERE target_url = 'https://rfclass.ru/'"
            ).fetchone()
            outdated_alias = connection.execute(
                """
                SELECT 1 FROM assistant_command_aliases
                WHERE normalized_phrase = 'откройрусскийрегистр'
                """
            ).fetchone()

        self.assertEqual(website["name"], "Российское классификационное общество (РКО)")
        self.assertIsNone(outdated_alias)

    def test_repeated_seed_does_not_create_duplicates(self) -> None:
        seed_reference_data(self.database_path)
        seed_reference_data(self.database_path)

        with get_connection(self.database_path) as connection:
            customer_count = connection.execute(
                "SELECT COUNT(*) AS count FROM customers"
            ).fetchone()["count"]
            object_count = connection.execute(
                "SELECT COUNT(*) AS count FROM project_objects"
            ).fetchone()["count"]
            command_alias_count = connection.execute(
                "SELECT COUNT(*) AS count FROM assistant_command_aliases"
            ).fetchone()["count"]
            action_count = connection.execute(
                "SELECT COUNT(*) AS count FROM assistant_actions"
            ).fetchone()["count"]
            website_count = connection.execute(
                "SELECT COUNT(*) AS count FROM assistant_websites"
            ).fetchone()["count"]

        self.assertEqual(customer_count, len(SEED_CUSTOMERS))
        self.assertEqual(object_count, len(SEED_PROJECT_OBJECTS))
        self.assertEqual(
            command_alias_count,
            len(SEED_ASSISTANT_COMMAND_ALIASES) + len(SEED_ASSISTANT_SITE_COMMAND_ALIASES),
        )
        self.assertEqual(action_count, len(SEED_ASSISTANT_ACTIONS))
        self.assertEqual(website_count, len(SEED_ASSISTANT_WEBSITES))


if __name__ == "__main__":
    unittest.main()
