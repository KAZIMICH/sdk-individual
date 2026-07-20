"""Запросы к справочнику заказчиков."""

from dataclasses import dataclass
from pathlib import Path

from app.config import DATABASE_PATH
from app.database import get_connection
from app.repositories.errors import RecordNotFoundError


@dataclass(frozen=True)
class Customer:
    id: int
    name: str
    director: str


def list_customers(database_path: Path = DATABASE_PATH) -> list[Customer]:
    """Вернуть заказчиков в алфавитном порядке."""
    with get_connection(database_path) as connection:
        rows = connection.execute(
            "SELECT id, name, director FROM customers ORDER BY name"
        ).fetchall()

    return [Customer(id=row["id"], name=row["name"], director=row["director"]) for row in rows]


def get_customer(customer_id: int, database_path: Path = DATABASE_PATH) -> Customer:
    """Вернуть заказчика по идентификатору."""
    with get_connection(database_path) as connection:
        row = connection.execute(
            "SELECT id, name, director FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()

    if row is None:
        raise RecordNotFoundError(f"Заказчик с id={customer_id} не найден.")

    return Customer(id=row["id"], name=row["name"], director=row["director"])
