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
            {"customers", "project_objects", "documents", "document_work_items"}
            <= table_names
        )

    def test_document_references_customer_and_project_object(self) -> None:
        with get_connection(self.database_path) as connection:
            foreign_keys = connection.execute("PRAGMA foreign_key_list(documents)").fetchall()

        referenced_tables = {row["table"] for row in foreign_keys}
        self.assertEqual(referenced_tables, {"customers", "project_objects"})

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
