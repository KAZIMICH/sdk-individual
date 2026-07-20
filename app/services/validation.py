"""Серверная валидация данных формы создания документа."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.config import DATABASE_PATH
from app.repositories.customers import get_customer
from app.repositories.documents import DocumentCreateData, WorkItemInput
from app.repositories.errors import RecordNotFoundError
from app.repositories.project_objects import get_project_object


class FormValidationError(ValueError):
    """Данные формы не прошли проверку."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("Данные формы не прошли проверку.")
        self.errors = errors


@dataclass(frozen=True)
class DocumentFormInput:
    customer_id: object
    object_id: object
    subject: object
    amount: object
    lead_time_days: object
    validity_period_days: object
    work_items: list[WorkItemInput]


def validate_document_form(
    form: DocumentFormInput, database_path: Path = DATABASE_PATH
) -> DocumentCreateData:
    """Проверить форму и подготовить данные для сохранения в SQLite."""
    errors: dict[str, str] = {}

    customer_id = _parse_positive_integer(form.customer_id, "customer_id", errors)
    object_id = _parse_positive_integer(form.object_id, "object_id", errors)
    subject = _parse_required_text(form.subject, "subject", errors)
    amount_kopecks = _parse_amount_kopecks(form.amount, errors)
    lead_time_days = _parse_positive_integer(form.lead_time_days, "lead_time_days", errors)
    validity_period_days = _parse_positive_integer(
        form.validity_period_days, "validity_period_days", errors
    )
    work_items = _validate_work_items(form.work_items, errors)

    if customer_id is not None:
        try:
            get_customer(customer_id, database_path)
        except RecordNotFoundError:
            errors["customer_id"] = "Выбранный заказчик не найден."

    if object_id is not None:
        try:
            get_project_object(object_id, database_path)
        except RecordNotFoundError:
            errors["object_id"] = "Выбранный объект проекта не найден."

    if errors:
        raise FormValidationError(errors)

    return DocumentCreateData(
        customer_id=customer_id,
        object_id=object_id,
        subject=subject,
        amount_kopecks=amount_kopecks,
        lead_time_days=lead_time_days,
        validity_period_days=validity_period_days,
        work_items=work_items,
    )


def _parse_positive_integer(value: object, field: str, errors: dict[str, str]) -> int | None:
    if isinstance(value, bool):
        errors[field] = "Значение должно быть положительным целым числом."
        return None

    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        errors[field] = "Значение должно быть положительным целым числом."
        return None

    if number <= 0 or str(value).strip() != str(number):
        errors[field] = "Значение должно быть положительным целым числом."
        return None

    return number


def _parse_required_text(value: object, field: str, errors: dict[str, str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors[field] = "Поле обязательно для заполнения."
        return None
    return value.strip()


def _parse_amount_kopecks(value: object, errors: dict[str, str]) -> int | None:
    if isinstance(value, bool):
        errors["amount"] = "Сумма должна быть положительным числом с точностью до копеек."
        return None

    try:
        amount = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        errors["amount"] = "Сумма должна быть положительным числом с точностью до копеек."
        return None

    if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
        errors["amount"] = "Сумма должна быть положительным числом с точностью до копеек."
        return None

    return int(amount * 100)


def _validate_work_items(
    work_items: list[WorkItemInput], errors: dict[str, str]
) -> list[WorkItemInput]:
    if not work_items:
        errors["work_items"] = "Добавьте хотя бы одну строку состава работ."
        return []

    validated_items: list[WorkItemInput] = []
    for index, item in enumerate(work_items, start=1):
        name = _parse_required_text(item.name, f"work_items.{index}.name", errors)
        comment = item.comment.strip() if isinstance(item.comment, str) and item.comment.strip() else None
        if name is not None:
            validated_items.append(WorkItemInput(name=name, comment=comment))

    return validated_items
