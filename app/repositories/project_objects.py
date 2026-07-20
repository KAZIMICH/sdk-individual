"""Запросы к справочнику объектов проекта."""

from dataclasses import dataclass
from pathlib import Path

from app.config import DATABASE_PATH
from app.database import get_connection
from app.repositories.errors import RecordNotFoundError


@dataclass(frozen=True)
class ProjectObject:
    id: int
    name: str
    imo: str


def list_project_objects(database_path: Path = DATABASE_PATH) -> list[ProjectObject]:
    """Вернуть объекты проекта в алфавитном порядке."""
    with get_connection(database_path) as connection:
        rows = connection.execute(
            "SELECT id, name, imo FROM project_objects ORDER BY name"
        ).fetchall()

    return [ProjectObject(id=row["id"], name=row["name"], imo=row["imo"]) for row in rows]


def get_project_object(
    object_id: int, database_path: Path = DATABASE_PATH
) -> ProjectObject:
    """Вернуть объект проекта по идентификатору."""
    with get_connection(database_path) as connection:
        row = connection.execute(
            "SELECT id, name, imo FROM project_objects WHERE id = ?", (object_id,)
        ).fetchone()

    if row is None:
        raise RecordNotFoundError(f"Объект проекта с id={object_id} не найден.")

    return ProjectObject(id=row["id"], name=row["name"], imo=row["imo"])
