"""Проверки репозиториев заказчиков и объектов проекта."""

import tempfile
import unittest
from pathlib import Path

from app.models import initialize_database
from app.repositories.customers import get_customer, list_customers
from app.repositories.errors import RecordNotFoundError
from app.repositories.project_objects import get_project_object, list_project_objects
from scripts.init_db import SEED_CUSTOMERS, SEED_PROJECT_OBJECTS, seed_reference_data


class ReferenceRepositoriesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "test.db"
        initialize_database(self.database_path)
        seed_reference_data(self.database_path)

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_lists_customers_and_returns_one_customer(self) -> None:
        customers = list_customers(self.database_path)

        self.assertEqual(
            [customer.name for customer in customers],
            sorted(customer[0] for customer in SEED_CUSTOMERS),
        )
        self.assertEqual(get_customer(customers[0].id, self.database_path), customers[0])

    def test_lists_objects_and_returns_one_object(self) -> None:
        project_objects = list_project_objects(self.database_path)

        self.assertEqual(len(project_objects), len(SEED_PROJECT_OBJECTS))
        self.assertEqual(
            get_project_object(project_objects[0].id, self.database_path), project_objects[0]
        )

    def test_raises_error_for_unknown_reference_ids(self) -> None:
        with self.assertRaises(RecordNotFoundError):
            get_customer(999, self.database_path)

        with self.assertRaises(RecordNotFoundError):
            get_project_object(999, self.database_path)


if __name__ == "__main__":
    unittest.main()
