"""Проверки сохранения записи документа до генерации файла."""

import tempfile
import unittest
from pathlib import Path

from app.database import get_connection
from app.models import initialize_database
from app.repositories.documents import (
    DocumentCreateData,
    WorkItemInput,
    create_document,
)
from app.repositories.errors import RecordNotFoundError
from app.repositories.project_objects import list_project_objects
from app.repositories.customers import list_customers
from scripts.init_db import seed_reference_data


class DocumentRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "test.db"
        initialize_database(self.database_path)
        seed_reference_data(self.database_path)
        self.customer = list_customers(self.database_path)[0]
        self.project_object = list_project_objects(self.database_path)[1]

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def make_data(self, **overrides: object) -> DocumentCreateData:
        values: dict[str, object] = {
            "customer_id": self.customer.id,
            "object_id": self.project_object.id,
            "subject": "Подготовка документации",
            "amount_kopecks": 12500050,
            "lead_time_days": 21,
            "validity_period_days": 30,
            "work_items": [
                WorkItemInput("Разработка документации", "Согласно ТЗ"),
                WorkItemInput("Согласование"),
            ],
        }
        values.update(overrides)
        return DocumentCreateData(**values)  # type: ignore[arg-type]

    def test_creates_pending_document_and_keeps_selected_references(self) -> None:
        created = create_document(self.make_data(), self.database_path)

        with get_connection(self.database_path) as connection:
            document = connection.execute(
                "SELECT customer_id, object_id, status FROM documents WHERE id = ?",
                (created.id,),
            ).fetchone()

        self.assertEqual(created.status, "pending")
        self.assertEqual(document["customer_id"], self.customer.id)
        self.assertEqual(document["object_id"], self.project_object.id)
        self.assertEqual(document["status"], "pending")

    def test_saves_work_items_in_form_order(self) -> None:
        created = create_document(self.make_data(), self.database_path)

        with get_connection(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT position, name, comment
                FROM document_work_items
                WHERE document_id = ?
                ORDER BY position
                """,
                (created.id,),
            ).fetchall()

        self.assertEqual(
            [(row["position"], row["name"], row["comment"]) for row in rows],
            [
                (1, "Разработка документации", "Согласно ТЗ"),
                (2, "Согласование", None),
            ],
        )

    def test_does_not_create_document_for_unknown_reference(self) -> None:
        with self.assertRaises(RecordNotFoundError):
            create_document(self.make_data(customer_id=999), self.database_path)

        with get_connection(self.database_path) as connection:
            document_count = connection.execute(
                "SELECT COUNT(*) AS count FROM documents"
            ).fetchone()["count"]

        self.assertEqual(document_count, 0)


if __name__ == "__main__":
    unittest.main()
