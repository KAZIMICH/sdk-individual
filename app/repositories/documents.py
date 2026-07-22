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


@dataclass(frozen=True)
class DocumentListItem:
    id: int
    customer_name: str
    object_name: str
    subject: str
    created_at: str
    status: str


@dataclass(frozen=True)
class DocumentGenerationData:
    id: int
    customer_name: str
    director: str
    object_name: str
    object_imo: str
    subject: str
    amount_kopecks: int
    lead_time_days: int
    validity_period_days: int
    work_items: list[WorkItemInput]


def list_documents(
    search: str = "", database_path: Path = DATABASE_PATH
) -> list[DocumentListItem]:
    """Вернуть документы; при поиске — по заказчику или объекту проекта."""
    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT
                documents.id,
                customers.name AS customer_name,
                project_objects.name AS object_name,
                documents.subject,
                documents.created_at,
                documents.status
            FROM documents
            JOIN customers ON customers.id = documents.customer_id
            JOIN project_objects ON project_objects.id = documents.object_id
            ORDER BY documents.created_at DESC, documents.id DESC
            """
        ).fetchall()

    documents = [
        DocumentListItem(
            id=row["id"],
            customer_name=row["customer_name"],
            object_name=row["object_name"],
            subject=row["subject"],
            created_at=row["created_at"],
            status=row["status"],
        )
        for row in rows
    ]
    normalized_search = search.strip().casefold()
    if not normalized_search:
        return documents

    return [
        document
        for document in documents
        if normalized_search in document.customer_name.casefold()
        or normalized_search in document.object_name.casefold()
    ]


def get_document_generation_data(
    document_id: int, database_path: Path = DATABASE_PATH
) -> DocumentGenerationData:
    """Вернуть все данные документа, нужные для рендеринга Word-шаблона."""
    with get_connection(database_path) as connection:
        row = connection.execute(
            """
            SELECT
                documents.id, customers.name AS customer_name, customers.director,
                project_objects.name AS object_name, project_objects.imo AS object_imo,
                documents.subject, documents.amount_kopecks, documents.lead_time_days,
                documents.validity_period_days
            FROM documents
            JOIN customers ON customers.id = documents.customer_id
            JOIN project_objects ON project_objects.id = documents.object_id
            WHERE documents.id = ?
            """,
            (document_id,),
        ).fetchone()
        work_item_rows = connection.execute(
            """
            SELECT name, comment FROM document_work_items
            WHERE document_id = ? ORDER BY position
            """,
            (document_id,),
        ).fetchall()

    if row is None:
        raise RecordNotFoundError(f"Документ с id={document_id} не найден.")

    return DocumentGenerationData(
        id=row["id"],
        customer_name=row["customer_name"],
        director=row["director"],
        object_name=row["object_name"],
        object_imo=row["object_imo"],
        subject=row["subject"],
        amount_kopecks=row["amount_kopecks"],
        lead_time_days=row["lead_time_days"],
        validity_period_days=row["validity_period_days"],
        work_items=[WorkItemInput(name=item["name"], comment=item["comment"]) for item in work_item_rows],
    )


def set_document_generation_status(
    document_id: int,
    status: str,
    error_message: str | None = None,
    database_path: Path = DATABASE_PATH,
) -> None:
    """Сохранить итоговый статус попытки генерации документа."""
    with get_connection(database_path) as connection:
        result = connection.execute(
            "UPDATE documents SET status = ?, error_message = ? WHERE id = ?",
            (status, error_message, document_id),
        )

    if result.rowcount == 0:
        raise RecordNotFoundError(f"Документ с id={document_id} не найден.")


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
