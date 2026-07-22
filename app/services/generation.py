"""Генерация Word-документа из сохранённой записи и шаблона."""

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from docxtpl import DocxTemplate
from num2words import num2words

from app.config import DATABASE_PATH, DOCUMENT_TEMPLATES_DIR, GENERATED_DOCUMENTS_DIR
from app.repositories.documents import (
    DocumentGenerationData,
    get_document_generation_data,
    set_document_generation_status,
)
from app.services.storage import prepare_and_save_document_path


class DocumentGenerationError(RuntimeError):
    """Не удалось сформировать Word-документ."""


def generate_document(
    document_id: int,
    database_path: Path = DATABASE_PATH,
    template_path: Path = DOCUMENT_TEMPLATES_DIR / "CP_ver.01.docx",
    output_directory: Path = GENERATED_DOCUMENTS_DIR,
) -> Path:
    """Сформировать `.docx`, сохранить его и обновить статус документа."""
    data = get_document_generation_data(document_id, database_path)
    try:
        output_path = prepare_and_save_document_path(
            document_id, database_path, output_directory
        )
        if output_path.exists():
            raise FileExistsError(f"Файл документа уже существует: {output_path.name}")

        document = DocxTemplate(template_path)
        document.render(_build_template_context(data))
        document.save(output_path)
    except Exception as error:
        set_document_generation_status(
            document_id, "error", str(error)[:500], database_path
        )
        raise DocumentGenerationError("Не удалось сформировать документ.") from error

    set_document_generation_status(document_id, "generated", database_path=database_path)
    return output_path


def _build_template_context(data: DocumentGenerationData) -> dict[str, object]:
    amount = Decimal(data.amount_kopecks) / Decimal(100)
    return {
        "customer_name": data.customer_name,
        "director": data.director,
        "object_name": data.object_name,
        "object_imo": data.object_imo,
        "subject": data.subject,
        "proposal_rows": [
            {"name": item.name, "comment": item.comment or ""} for item in data.work_items
        ],
        "amount_full_text": _format_amount(amount),
        "lead_time_text": _days_text(data.lead_time_days),
        "validity_period_text": _days_text(data.validity_period_days, case="genitive"),
    }


def _days_text(days: int, case: str = "nominative") -> str:
    """Вернуть количество дней в нужном падеже для фразы шаблона."""
    number = f"{days:,}".replace(",", " ")
    words = num2words(days, lang="ru", case=case)
    if case == "genitive":
        day_word = _genitive_days_plural(days)
    else:
        day_word = _russian_plural(days, "день", "дня", "дней")
    return f"{number} ({words}) {day_word}"


def _format_amount(amount: Decimal) -> str:
    """Вернуть сумму без копеек: цифрами, прописью и со склонением рубля."""
    rounded_amount = int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    number = f"{rounded_amount:,}".replace(",", " ")
    words = num2words(rounded_amount, lang="ru")
    return f"{number} ({words}) {_russian_plural(rounded_amount, 'рубль', 'рубля', 'рублей')}"


def _russian_plural(value: int, one: str, few: str, many: str) -> str:
    """Выбрать форму существительного для положительного целого числа."""
    remainder = value % 100
    if 11 <= remainder <= 14:
        return many
    if value % 10 == 1:
        return one
    if 2 <= value % 10 <= 4:
        return few
    return many


def _genitive_days_plural(days: int) -> str:
    """Вернуть форму «дня/дней» после оборота «в течение»."""
    return "дня" if days % 10 == 1 and not 11 <= days % 100 <= 14 else "дней"
