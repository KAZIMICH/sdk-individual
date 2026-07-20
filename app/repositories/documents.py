"""Создание записей документов и строк состава работ."""

from dataclasses import dataclass
from pathlib import Path

from app.config import DATABASE_PATH
from app.database import get_connection
from app.repositories.customers import get_customer
from app.repositories.errors import RecordNotFoundError
from app.repositories.project_objects import get_project_object


@dataclass(frozen=True)
class WorkItemInput:
    name: str
    comment: str | None = None


@dataclass(frozen=True)
class DocumentCreateData:
    customer_id: int
    object_id: int
    subject: str
    amount_kopecks: int
    lead_time_days: int
    validity_period_days: int
    work_items: list[WorkItemInput]


@dataclass(frozen=True)
class CreatedDocument:
    id: int
    status: str


def create_document(
    data: DocumentCreateData, database_path: Path = DATABASE_PATH
) -> CreatedDocument:
    """Сохранить документ со строками состава работ до генерации файла."""
    get_customer(data.customer_id, database_path)
    get_project_object(data.object_id, database_path)

    with get_connection(database_path) as connection:
        document_id = connection.execute(
            """
            INSERT INTO documents (
                customer_id, object_id, subject, amount_kopecks,
                lead_time_days, validity_period_days, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                data.customer_id,
                data.object_id,
                data.subject,
                data.amount_kopecks,
                data.lead_time_days,
                data.validity_period_days,
            ),
        ).lastrowid

        connection.executemany(
            """
            INSERT INTO document_work_items (document_id, position, name, comment)
            VALUES (?, ?, ?, ?)
            """,
            [
                (document_id, position, item.name, item.comment)
                for position, item in enumerate(data.work_items, start=1)
            ],
        )

    return CreatedDocument(id=document_id, status="pending")


def set_document_file_path(
    document_id: int, file_path: str, database_path: Path = DATABASE_PATH
) -> None:
    """Сохранить будущий или фактический путь к файлу документа."""
    with get_connection(database_path) as connection:
        result = connection.execute(
            "UPDATE documents SET file_path = ? WHERE id = ?", (file_path, document_id)
        )

    if result.rowcount == 0:
        raise RecordNotFoundError(f"Документ с id={document_id} не найден.")


def get_document_customer_id(
    document_id: int, database_path: Path = DATABASE_PATH
) -> int:
    """Вернуть идентификатор заказчика, связанного с документом."""
    with get_connection(database_path) as connection:
        row = connection.execute(
            "SELECT customer_id FROM documents WHERE id = ?", (document_id,)
        ).fetchone()

    if row is None:
        raise RecordNotFoundError(f"Документ с id={document_id} не найден.")

    return row["customer_id"]
