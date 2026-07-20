"""Проверки начального заполнения SQLite."""

import tempfile
import unittest
from pathlib import Path

from app.database import get_connection
from app.models import initialize_database
from scripts.init_db import (
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

        self.assertEqual(customer_count, len(SEED_CUSTOMERS))
        self.assertEqual(object_count, len(SEED_PROJECT_OBJECTS))

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

        self.assertEqual(customer_count, len(SEED_CUSTOMERS))
        self.assertEqual(object_count, len(SEED_PROJECT_OBJECTS))


if __name__ == "__main__":
    unittest.main()
