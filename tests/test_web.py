"""Проверка точки входа frontend без проверки backend-логики."""

import unittest

from fastapi.testclient import TestClient

from app.main import app


class WebTests(unittest.TestCase):
    def test_documents_list_page_is_served(self) -> None:
        with TestClient(app) as client:
            response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Список КП", response.text)


if __name__ == "__main__":
    unittest.main()
