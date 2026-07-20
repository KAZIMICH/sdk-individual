"""Проверки файлов, необходимых для воспроизводимого развёртывания."""

import unittest

from app.config import (
    DOCUMENT_TEMPLATES_DIR,
    GENERATED_DOCUMENTS_DIR,
    PROJECT_ROOT,
)


class DeploymentStructureTests(unittest.TestCase):
    def test_deployment_files_exist(self) -> None:
        for filename in ("README.md", ".env.example", "requirements.txt"):
            self.assertTrue((PROJECT_ROOT / filename).is_file())

    def test_environment_example_declares_storage_settings(self) -> None:
        content = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
        for setting in (
            "DATABASE_PATH=",
            "DOCUMENT_TEMPLATES_DIR=",
            "GENERATED_DOCUMENTS_DIR=",
        ):
            self.assertIn(setting, content)

    def test_required_document_directories_exist(self) -> None:
        self.assertTrue(DOCUMENT_TEMPLATES_DIR.is_dir())
        self.assertTrue(GENERATED_DOCUMENTS_DIR.is_dir())
        self.assertTrue((DOCUMENT_TEMPLATES_DIR / "CP_ver.01.docx").is_file())


if __name__ == "__main__":
    unittest.main()
