"""Подготовка каталогов и путей для файлов документов."""

import re
from datetime import date
from pathlib import Path

from app.config import DATABASE_PATH, GENERATED_DOCUMENTS_DIR
from app.repositories.customers import get_customer
from app.repositories.documents import get_document_customer_id, set_document_file_path


def sanitize_customer_folder_name(customer_name: str) -> str:
    """Вернуть имя папки, безопасное для Windows и Linux."""
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", customer_name).strip(". ")
    if not sanitized:
        return "customer"
    if sanitized.upper() in {"CON", "PRN", "AUX", "NUL", "COM1", "LPT1"}:
        return f"{sanitized}_"
    return sanitized


def prepare_document_path(
    document_id: int,
    customer_name: str,
    output_directory: Path = GENERATED_DOCUMENTS_DIR,
    created_on: date | None = None,
) -> Path:
    """Создать папку заказчика и сформировать путь к будущему Word-файлу."""
    current_date = created_on or date.today()
    customer_directory = output_directory / sanitize_customer_folder_name(customer_name)
    customer_directory.mkdir(parents=True, exist_ok=True)
    filename = f"{current_date:%Y_%m_%d}_CP_{document_id:03d}.docx"
    return customer_directory / filename


def prepare_and_save_document_path(
    document_id: int,
    database_path: Path = DATABASE_PATH,
    output_directory: Path = GENERATED_DOCUMENTS_DIR,
    created_on: date | None = None,
) -> Path:
    """Подготовить путь и сохранить его в записи документа до генерации файла."""
    customer_id = get_document_customer_id(document_id, database_path)
    customer = get_customer(customer_id, database_path)
    file_path = prepare_document_path(
        document_id=document_id,
        customer_name=customer.name,
        output_directory=output_directory,
        created_on=created_on,
    )
    set_document_file_path(document_id, str(file_path), database_path)
    return file_path
