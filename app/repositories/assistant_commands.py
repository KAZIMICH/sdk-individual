"""Чтение настроек команд рабочего ассистента из SQLite."""

from dataclasses import dataclass
from pathlib import Path

from app.config import DATABASE_PATH
from app.database import get_connection


@dataclass(frozen=True)
class AssistantCommandAlias:
    """Активный вариант команды и разрешённое действие."""

    phrase: str
    normalized_phrase: str
    action_code: str
    target_url: str | None
    requires_query: bool
    website_name: str | None


def list_active_command_aliases(
    database_path: Path = DATABASE_PATH,
) -> list[AssistantCommandAlias]:
    """Вернуть активные варианты команд в стабильном порядке."""
    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT aliases.phrase, aliases.normalized_phrase, aliases.action_code,
                   CASE
                       WHEN aliases.action_code = 'open_site' THEN websites.target_url
                       ELSE actions.target_url
                   END AS target_url,
                   actions.requires_query,
                   websites.name AS website_name
            FROM assistant_command_aliases AS aliases
            INNER JOIN assistant_actions AS actions
                ON actions.action_code = aliases.action_code
            LEFT JOIN assistant_websites AS websites
                ON websites.id = aliases.website_id
            WHERE aliases.is_active = 1
                AND actions.is_active = 1
                AND (aliases.action_code <> 'open_site' OR websites.is_active = 1)
            ORDER BY aliases.id
            """
        ).fetchall()

    return [
        AssistantCommandAlias(
            phrase=row["phrase"],
            normalized_phrase=row["normalized_phrase"],
            action_code=row["action_code"],
            target_url=row["target_url"],
            requires_query=bool(row["requires_query"]),
            website_name=row["website_name"],
        )
        for row in rows
    ]
