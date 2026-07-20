"""Проверки базовой конфигурации приложения."""

import unittest
from pathlib import Path

from app.config import (
    DATA_DIR,
    DATABASE_PATH,
    DOCUMENT_TEMPLATES_DIR,
    GENERATED_DOCUMENTS_DIR,
    PROJECT_ROOT,
)


class ConfigPathsTests(unittest.TestCase):
    def test_project_root_is_workspace(self) -> None:
        self.assertEqual(PROJECT_ROOT, Path(__file__).resolve().parent.parent)

    def test_data_paths_are_inside_data_directory(self) -> None:
        self.assertEqual(DATABASE_PATH.parent, DATA_DIR)
        self.assertEqual(DATA_DIR, PROJECT_ROOT / "data")

    def test_document_directories_exist(self) -> None:
        self.assertTrue(DOCUMENT_TEMPLATES_DIR.is_dir())
        self.assertTrue(GENERATED_DOCUMENTS_DIR.is_dir())


if __name__ == "__main__":
    unittest.main()
