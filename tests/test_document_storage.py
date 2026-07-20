"""Проверки подготовки путей к генерируемым документам."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.database import get_connection
from app.models import initialize_database
from app.repositories.customers import list_customers
from app.repositories.documents import DocumentCreateData, WorkItemInput, create_document
from app.repositories.errors import RecordNotFoundError
from app.repositories.project_objects import list_project_objects
from app.services.storage import (
    prepare_and_save_document_path,
    sanitize_customer_folder_name,
)
from scripts.init_db import seed_reference_data


class DocumentStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)
        self.database_path = self.root / "test.db"
        self.output_directory = self.root / "generated_CP"
        initialize_database(self.database_path)
        seed_reference_data(self.database_path)
        self.customer = list_customers(self.database_path)[0]
        self.project_object = list_project_objects(self.database_path)[0]
        self.document = create_document(
            DocumentCreateData(
                customer_id=self.customer.id,
                object_id=self.project_object.id,
                subject="Тест",
                amount_kopecks=10000,
                lead_time_days=10,
                validity_period_days=30,
                work_items=[WorkItemInput("Тестовая работа")],
            ),
            self.database_path,
        )

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_creates_customer_directory_and_saves_future_path(self) -> None:
        file_path = prepare_and_save_document_path(
            document_id=self.document.id,
            database_path=self.database_path,
            output_directory=self.output_directory,
            created_on=date(2026, 7, 20),
        )

        self.assertTrue(file_path.parent.is_dir())
        self.assertEqual(file_path.name, "2026_07_20_CP_001.docx")
        self.assertFalse(file_path.exists())
        with get_connection(self.database_path) as connection:
            saved_path = connection.execute(
                "SELECT file_path FROM documents WHERE id = ?", (self.document.id,)
            ).fetchone()["file_path"]
        self.assertEqual(saved_path, str(file_path))

    def test_sanitizes_customer_folder_name(self) -> None:
        self.assertEqual(sanitize_customer_folder_name('ООО: Тест/Проект'), "ООО_ Тест_Проект")
        self.assertEqual(sanitize_customer_folder_name("CON"), "CON_")

    def test_rejects_unknown_document_when_saving_path(self) -> None:
        with self.assertRaises(RecordNotFoundError):
            prepare_and_save_document_path(
                document_id=999,
                database_path=self.database_path,
                output_directory=self.output_directory,
            )
