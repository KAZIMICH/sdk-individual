"""HTTP-проверки FastAPI-приложения."""

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.models import initialize_database
from scripts.init_db import SEED_CUSTOMERS, SEED_PROJECT_OBJECTS, seed_reference_data


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "test.db"
        initialize_database(self.database_path)
        seed_reference_data(self.database_path)
        self.previous_database_path = app.state.database_path
        self.previous_template_path = app.state.document_template_path
        self.previous_output_directory = app.state.generated_documents_directory
        app.state.database_path = self.database_path
        app.state.document_template_path = Path("document_templates/CP_ver.01.docx").resolve()
        app.state.generated_documents_directory = Path(self.temp_directory.name) / "generated_CP"

    def tearDown(self) -> None:
        app.state.database_path = self.previous_database_path
        app.state.document_template_path = self.previous_template_path
        app.state.generated_documents_directory = self.previous_output_directory
        self.temp_directory.cleanup()

    def test_health_endpoint_returns_ok(self) -> None:
        with TestClient(app) as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_reference_endpoints_return_seeded_data(self) -> None:
        with TestClient(app) as client:
            customers = client.get("/api/customers")
            project_objects = client.get("/api/project-objects")

            customer = client.get(f"/api/customers/{customers.json()[0]['id']}")
            project_object = client.get(
                f"/api/project-objects/{project_objects.json()[0]['id']}"
            )

        self.assertEqual(customers.status_code, 200)
        self.assertEqual(len(customers.json()), len(SEED_CUSTOMERS))
        self.assertEqual(customer.status_code, 200)
        self.assertIn("director", customer.json())
        self.assertEqual(project_objects.status_code, 200)
        self.assertEqual(len(project_objects.json()), len(SEED_PROJECT_OBJECTS))
        self.assertEqual(project_object.status_code, 200)
        self.assertIn("imo", project_object.json())

    def test_unknown_reference_returns_not_found(self) -> None:
        with TestClient(app) as client:
            response = client.get("/api/customers/999")

        self.assertEqual(response.status_code, 404)

    def test_creates_pending_document_from_valid_payload(self) -> None:
        with TestClient(app) as client:
            customer_id = client.get("/api/customers").json()[0]["id"]
            object_id = client.get("/api/project-objects").json()[0]["id"]
            response = client.post(
                "/api/documents",
                json={
                    "customer_id": customer_id,
                    "object_id": object_id,
                    "subject": "Подготовка документации",
                    "amount": "125000,50",
                    "lead_time_days": 21,
                    "validity_period_days": 30,
                    "work_items": [{"name": "Разработка", "comment": "Первый этап"}],
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "pending")
        self.assertIsInstance(response.json()["id"], int)

    def test_lists_documents_and_searches_by_customer_or_object(self) -> None:
        with TestClient(app) as client:
            customer_id = client.get("/api/customers").json()[0]["id"]
            object_id = client.get("/api/project-objects").json()[0]["id"]
            client.post(
                "/api/documents",
                json={
                    "customer_id": customer_id,
                    "object_id": object_id,
                    "subject": "Подготовка документации",
                    "amount": "125000,50",
                    "lead_time_days": 21,
                    "validity_period_days": 30,
                    "work_items": [{"name": "Разработка"}],
                },
            )
            documents = client.get("/api/documents")
            document = documents.json()[0]
            customer_search = client.get(
                "/api/documents", params={"search": document["customer_name"]}
            )
            object_search = client.get(
                "/api/documents", params={"search": document["object_name"]}
            )
            missing_search = client.get("/api/documents?search=нет%20совпадений")

        self.assertEqual(documents.status_code, 200)
        self.assertEqual(len(documents.json()), 1)
        self.assertEqual(documents.json()[0]["customer_name"], "ООО Альфа")
        self.assertEqual(customer_search.json(), documents.json())
        self.assertEqual(object_search.json(), documents.json())
        self.assertEqual(missing_search.json(), [])

    def test_generates_word_file_for_created_document(self) -> None:
        with TestClient(app) as client:
            customer_id = client.get("/api/customers").json()[0]["id"]
            object_id = client.get("/api/project-objects").json()[0]["id"]
            created = client.post(
                "/api/documents",
                json={
                    "customer_id": customer_id,
                    "object_id": object_id,
                    "subject": "Подготовка документации",
                    "amount": "125000,50",
                    "lead_time_days": 21,
                    "validity_period_days": 30,
                    "work_items": [{"name": "Разработка"}],
                },
            )
            response = client.post(f"/api/documents/{created.json()['id']}/generate")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "generated")

    def test_returns_field_errors_for_invalid_document_payload(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/api/documents",
                json={
                    "customer_id": 999,
                    "object_id": 999,
                    "subject": "",
                    "amount": "0",
                    "lead_time_days": 0,
                    "validity_period_days": 0,
                    "work_items": [],
                },
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            set(response.json()["detail"]["errors"]),
            {
                "customer_id",
                "object_id",
                "subject",
                "amount",
                "lead_time_days",
                "validity_period_days",
                "work_items",
            },
        )


if __name__ == "__main__":
    unittest.main()
