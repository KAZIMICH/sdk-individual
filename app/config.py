"""Централизованные пути и настройки приложения."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "app.db"
DOCUMENT_TEMPLATES_DIR = PROJECT_ROOT / "document_templates"
GENERATED_DOCUMENTS_DIR = PROJECT_ROOT / "generated_CP"
