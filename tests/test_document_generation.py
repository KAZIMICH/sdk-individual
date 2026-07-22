"""Проверки генерации Word-документа по шаблону."""

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

from app.database import get_connection
from app.models import initialize_database
from app.repositories.customers import list_customers
from app.repositories.documents import DocumentCreateData, WorkItemInput, create_document
from app.repositories.project_objects import list_project_objects
from app.services.generation import (
    DocumentGenerationError,
    _days_text,
    _format_amount,
    generate_document,
)
from scripts.init_db import seed_reference_data


class DocumentGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        root = Path(self.temp_directory.name)
        self.database_path = root / "test.db"
        self.output_directory = root / "generated_CP"
        self.template_path = Path("document_templates/CP_ver.01.docx")
        initialize_database(self.database_path)
        seed_reference_data(self.database_path)
        customer = list_customers(self.database_path)[0]
        project_object = list_project_objects(self.database_path)[0]
        self.document = create_document(
            DocumentCreateData(
                customer_id=customer.id,
                object_id=project_object.id,
                subject="Подготовка документации",
                amount_kopecks=12500050,
                lead_time_days=21,
                validity_period_days=30,
                work_items=[WorkItemInput("Разработка", "Первый этап")],
            ),
            self.database_path,
        )

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_generates_file_and_marks_document_as_generated(self) -> None:
        output_path = generate_document(
            self.document.id,
            self.database_path,
            self.template_path,
            self.output_directory,
        )

        self.assertTrue(output_path.is_file())
        with get_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT status, file_path, error_message FROM documents WHERE id = ?",
                (self.document.id,),
            ).fetchone()
        self.assertEqual(row["status"], "generated")
        self.assertEqual(row["file_path"], str(output_path))
        self.assertIsNone(row["error_message"])

        with ZipFile(output_path) as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("Подготовка документации", document_xml)
        self.assertIn("Разработка", document_xml)

    def test_marks_document_as_error_when_template_is_missing(self) -> None:
        with self.assertRaises(DocumentGenerationError):
            generate_document(
                self.document.id,
                self.database_path,
                self.template_path.parent / "missing.docx",
                self.output_directory,
            )

        with get_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT status, error_message FROM documents WHERE id = ?",
                (self.document.id,),
            ).fetchone()
        self.assertEqual(row["status"], "error")
        self.assertTrue(row["error_message"])

    def test_formats_amount_without_kopecks_and_with_russian_declension(self) -> None:
        self.assertEqual(
            _format_amount(Decimal("25000")),
            "25 000 (двадцать пять тысяч) рублей",
        )
        self.assertEqual(_format_amount(Decimal("1.50")), "2 (два) рубля")
        self.assertEqual(_format_amount(Decimal("21")), "21 (двадцать один) рубль")

    def test_formats_deadlines_with_number_words_and_russian_declension(self) -> None:
        self.assertEqual(_days_text(21), "21 (двадцать один) день")
        self.assertEqual(_days_text(30), "30 (тридцать) дней")
        self.assertEqual(_days_text(12, case="genitive"), "12 (двенадцати) дней")
        self.assertEqual(_days_text(21, case="genitive"), "21 (двадцати одного) дня")
