"""Автотесты схемы SQLite."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.database import get_connection
from app.models import initialize_database


class DatabaseSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "test.db"
        initialize_database(self.database_path)

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_creates_required_tables(self) -> None:
        with get_connection(self.database_path) as connection:
            table_names = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

        self.assertTrue(
            {
                "customers",
                "project_objects",
                "documents",
                "document_work_items",
                "assistant_websites",
                "assistant_command_aliases",
                "assistant_actions",
            }
            <= table_names
        )

    def test_document_references_customer_and_project_object(self) -> None:
        with get_connection(self.database_path) as connection:
            foreign_keys = connection.execute("PRAGMA foreign_key_list(documents)").fetchall()

        referenced_tables = {row["table"] for row in foreign_keys}
        self.assertEqual(referenced_tables, {"customers", "project_objects"})

    def test_site_command_requires_existing_website(self) -> None:
        with get_connection(self.database_path) as connection:
            website_id = connection.execute(
                "INSERT INTO assistant_websites (name, target_url) VALUES (?, ?)",
                ("Test site", "https://example.com/"),
            ).lastrowid

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO assistant_command_aliases (
                        phrase, normalized_phrase, action_code
                    ) VALUES (?, ?, ?)
                    """,
                    ("Open test site", "opentestsite", "open_site"),
                )

            connection.execute(
                """
                INSERT INTO assistant_command_aliases (
                    phrase, normalized_phrase, action_code, website_id
                ) VALUES (?, ?, ?, ?)
                """,
                ("Open test site", "opentestsite", "open_site", website_id),
            )

    def test_migrates_existing_assistant_settings_for_search(self) -> None:
        legacy_database_path = Path(self.temp_directory.name) / "legacy.db"
        with get_connection(legacy_database_path) as connection:
            connection.executescript(
                """
                CREATE TABLE assistant_command_aliases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phrase TEXT NOT NULL,
                    normalized_phrase TEXT NOT NULL UNIQUE,
                    action_code TEXT NOT NULL CHECK (action_code IN ('create_document', 'open_mail', 'web_search')),
                    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
                );
                INSERT INTO assistant_command_aliases (phrase, normalized_phrase, action_code)
                VALUES ('Создай КП', 'создайкп', 'create_document');
                INSERT INTO assistant_command_aliases (phrase, normalized_phrase, action_code)
                VALUES ('Найди', 'найди', 'web_search');

                CREATE TABLE assistant_actions (
                    action_code TEXT PRIMARY KEY CHECK (action_code IN ('create_document', 'open_mail', 'web_search')),
                    target_url TEXT,
                    requires_query INTEGER NOT NULL DEFAULT 0 CHECK (requires_query IN (0, 1)),
                    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
                );
                INSERT INTO assistant_actions (action_code, target_url)
                VALUES ('open_mail', 'https://e.mail.ru/');
                INSERT INTO assistant_actions (action_code, target_url, requires_query)
                VALUES ('web_search', 'https://yandex.ru/search/?text=', 1);
                """
            )

        initialize_database(legacy_database_path)

        with get_connection(legacy_database_path) as connection:
            alias = connection.execute(
                "SELECT phrase, action_code, website_id FROM assistant_command_aliases ORDER BY id"
            ).fetchall()
            schema = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'assistant_command_aliases'"
            ).fetchone()["sql"]
            action = connection.execute(
                "SELECT target_url, requires_query FROM assistant_actions WHERE action_code = 'open_mail'"
            ).fetchone()
            action_schema = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'assistant_actions'"
            ).fetchone()["sql"]

        self.assertEqual(
            [(row["phrase"], row["action_code"], row["website_id"]) for row in alias],
            [("Создай КП", "create_document", None), ("Найди", "web_search", None)],
        )
        self.assertIn("open_site", schema)
        self.assertIn("website_id", schema)
        self.assertEqual((action["target_url"], action["requires_query"]), ("https://e.mail.ru/", 0))
        self.assertIn("open_site", action_schema)
        self.assertIn("requires_query", action_schema)

    def test_work_items_are_deleted_with_document(self) -> None:
        with get_connection(self.database_path) as connection:
            customer_id = connection.execute(
                "INSERT INTO customers (name, director) VALUES (?, ?)",
                ("ООО Тест", "Иванов И.И."),
            ).lastrowid
            object_id = connection.execute(
                "INSERT INTO project_objects (name, imo) VALUES (?, ?)",
                ("Тестовый объект", "1234567"),
            ).lastrowid
            document_id = connection.execute(
                """
                INSERT INTO documents (
                    customer_id, object_id, subject, amount_kopecks,
                    lead_time_days, validity_period_days
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (customer_id, object_id, "Тест", 10000, 10, 30),
            ).lastrowid
            connection.execute(
                """
                INSERT INTO document_work_items (document_id, position, name)
                VALUES (?, ?, ?)
                """,
                (document_id, 1, "Тестовая работа"),
            )
            connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            remaining_items = connection.execute(
                "SELECT COUNT(*) AS count FROM document_work_items"
            ).fetchone()["count"]

        self.assertEqual(remaining_items, 0)

    def test_rejects_invalid_document_status(self) -> None:
        with get_connection(self.database_path) as connection:
            customer_id = connection.execute(
                "INSERT INTO customers (name, director) VALUES (?, ?)",
                ("ООО Тест", "Иванов И.И."),
            ).lastrowid
            object_id = connection.execute(
                "INSERT INTO project_objects (name, imo) VALUES (?, ?)",
                ("Тестовый объект", "1234567"),
            ).lastrowid

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO documents (
                        customer_id, object_id, subject, amount_kopecks,
                        lead_time_days, validity_period_days, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (customer_id, object_id, "Тест", 10000, 10, 30, "unknown"),
                )


if __name__ == "__main__":
    unittest.main()
