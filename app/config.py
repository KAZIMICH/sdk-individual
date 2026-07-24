"""Централизованные пути и настройки приложения."""

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _path_setting(name: str, default: Path) -> Path:
    """Вернуть абсолютный путь из переменной окружения или значение по умолчанию."""
    value = os.getenv(name)
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _port_setting() -> int:
    """Вернуть номер порта из окружения или стандартный локальный порт."""
    try:
        return int(os.getenv("PORT", "8000"))
    except ValueError:
        return 8000


APP_NAME = os.getenv("APP_NAME", "Рабочий ассистент")
APP_ENV = os.getenv("APP_ENV", "development")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = _port_setting()
DATA_DIR = _path_setting("DATA_DIR", PROJECT_ROOT / "data")
DATABASE_PATH = _path_setting("DATABASE_PATH", DATA_DIR / "app.db")
DOCUMENT_TEMPLATES_DIR = _path_setting(
    "DOCUMENT_TEMPLATES_DIR", PROJECT_ROOT / "document_templates"
)
GENERATED_DOCUMENTS_DIR = _path_setting(
    "GENERATED_DOCUMENTS_DIR", PROJECT_ROOT / "generated_CP"
)
