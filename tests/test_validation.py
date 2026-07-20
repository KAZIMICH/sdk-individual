"""Проверки серверной валидации формы документа."""

import tempfile
import unittest
from pathlib import Path

from app.database import get_connection
from app.models import initialize_database
from app.repositories.customers import list_customers
from app.repositories.documents import WorkItemInput, create_document
from app.repositories.project_objects import list_project_objects
from app.services.validation import (
    DocumentFormInput,
    FormValidationError,
    validate_document_form,
)
from scripts.init_db import seed_reference_data


class DocumentValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "test.db"
        initialize_database(self.database_path)
        seed_reference_data(self.database_path)
        self.customer = list_customers(self.database_path)[0]
        self.project_object = list_project_objects(self.database_path)[0]

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def valid_form(self, **overrides: object) -> DocumentFormInput:
        values: dict[str, object] = {
            "customer_id": str(self.customer.id),
            "object_id": str(self.project_object.id),
            "subject": " Подготовка документации ",
            "amount": "125000,50",
            "lead_time_days": "21",
            "validity_period_days": "30",
            "work_items": [WorkItemInput(" Работа ", " Комментарий ")],
        }
        values.update(overrides)
        return DocumentFormInput(**values)  # type: ignore[arg-type]

    def test_normalizes_valid_form_for_database(self) -> None:
        data = validate_document_form(self.valid_form(), self.database_path)

        self.assertEqual(data.subject, "Подготовка документации")
        self.assertEqual(data.amount_kopecks, 12500050)
        self.assertEqual(data.lead_time_days, 21)
        self.assertEqual(data.work_items, [WorkItemInput("Работа", "Комментарий")])

    def test_collects_field_errors_and_does_not_create_document(self) -> None:
        form = self.valid_form(
            subject=" ",
            amount="1.999",
            lead_time_days="0",
            work_items=[],
        )

        with self.assertRaises(FormValidationError) as context:
            validate_document_form(form, self.database_path)

        self.assertEqual(
            set(context.exception.errors),
            {"subject", "amount", "lead_time_days", "work_items"},
        )
        with get_connection(self.database_path) as connection:
            document_count = connection.execute(
                "SELECT COUNT(*) AS count FROM documents"
            ).fetchone()["count"]
        self.assertEqual(document_count, 0)

    def test_rejects_missing_reference_before_document_creation(self) -> None:
        form = self.valid_form(customer_id="999")

        with self.assertRaises(FormValidationError) as context:
            validate_document_form(form, self.database_path)

        self.assertEqual(context.exception.errors, {"customer_id": "Выбранный заказчик не найден."})

    def test_validated_data_can_create_pending_document(self) -> None:
        data = validate_document_form(self.valid_form(), self.database_path)
        created = create_document(data, self.database_path)

        self.assertEqual(created.status, "pending")


if __name__ == "__main__":
    unittest.main()
