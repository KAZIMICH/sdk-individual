"""Точка входа FastAPI-приложения."""

from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import (
    DATABASE_PATH,
    DOCUMENT_TEMPLATES_DIR,
    GENERATED_DOCUMENTS_DIR,
    PROJECT_ROOT,
)
from app.repositories.customers import get_customer, list_customers
from app.repositories.documents import WorkItemInput, create_document, list_documents
from app.repositories.errors import RecordNotFoundError
from app.repositories.project_objects import get_project_object, list_project_objects
from app.services.generation import DocumentGenerationError, generate_document
from app.services.validation import (
    DocumentFormInput,
    FormValidationError,
    validate_document_form,
)


app = FastAPI(title="Рабочий ассистент")
app.state.database_path = DATABASE_PATH
app.state.document_template_path = DOCUMENT_TEMPLATES_DIR / "CP_ver.01.docx"
app.state.generated_documents_directory = GENERATED_DOCUMENTS_DIR
WEB_DIRECTORY = PROJECT_ROOT / "app" / "web"
app.mount("/static", StaticFiles(directory=WEB_DIRECTORY / "static"), name="static")


class WorkItemPayload(BaseModel):
    """Одна строка состава работ из HTTP-запроса."""

    name: str
    comment: str | None = None


class DocumentCreatePayload(BaseModel):
    """Данные формы создания документа."""

    customer_id: object
    object_id: object
    subject: object
    amount: object
    lead_time_days: object
    validity_period_days: object
    work_items: list[WorkItemPayload]


@app.get("/health")
def health_check() -> dict[str, str]:
    """Вернуть статус доступности backend-приложения."""
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def web_application() -> FileResponse:
    """Вернуть frontend-экран списка коммерческих предложений."""
    return FileResponse(WEB_DIRECTORY / "templates" / "index.html")


@app.get("/api/customers")
def customers(request: Request) -> list[dict[str, object]]:
    """Вернуть справочник заказчиков."""
    return [asdict(customer) for customer in list_customers(request.app.state.database_path)]


@app.get("/api/customers/{customer_id}")
def customer(customer_id: int, request: Request) -> dict[str, object]:
    """Вернуть данные заказчика для автоподстановки в форму."""
    try:
        return asdict(get_customer(customer_id, request.app.state.database_path))
    except RecordNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@app.get("/api/project-objects")
def project_objects(request: Request) -> list[dict[str, object]]:
    """Вернуть справочник объектов проекта."""
    return [
        asdict(project_object)
        for project_object in list_project_objects(request.app.state.database_path)
    ]


@app.get("/api/project-objects/{object_id}")
def project_object(object_id: int, request: Request) -> dict[str, object]:
    """Вернуть данные объекта для автоподстановки в форму."""
    try:
        return asdict(get_project_object(object_id, request.app.state.database_path))
    except RecordNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@app.post("/api/documents", status_code=status.HTTP_201_CREATED)
def document(payload: DocumentCreatePayload, request: Request) -> dict[str, object]:
    """Проверить форму и создать запись документа до генерации файла."""
    form = DocumentFormInput(
        customer_id=payload.customer_id,
        object_id=payload.object_id,
        subject=payload.subject,
        amount=payload.amount,
        lead_time_days=payload.lead_time_days,
        validity_period_days=payload.validity_period_days,
        work_items=[
            WorkItemInput(name=item.name, comment=item.comment) for item in payload.work_items
        ],
    )
    try:
        data = validate_document_form(form, request.app.state.database_path)
    except FormValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"errors": error.errors},
        ) from error

    created = create_document(data, request.app.state.database_path)
    return asdict(created)


@app.get("/api/documents")
def documents(request: Request, search: str = "") -> list[dict[str, object]]:
    """Вернуть сохранённые документы с поиском по заказчику или объекту."""
    return [
        asdict(document)
        for document in list_documents(search, request.app.state.database_path)
    ]


@app.post("/api/documents/{document_id}/generate")
def generate_document_file(document_id: int, request: Request) -> dict[str, object]:
    """Сформировать Word-файл для уже созданной записи документа."""
    try:
        generate_document(
            document_id,
            request.app.state.database_path,
            request.app.state.document_template_path,
            request.app.state.generated_documents_directory,
        )
    except RecordNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except DocumentGenerationError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сформировать Word-документ.",
        ) from error
    return {"id": document_id, "status": "generated"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
