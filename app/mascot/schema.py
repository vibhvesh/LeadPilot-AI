"""Idempotent schema step for mascot preferences on existing databases."""

from sqlalchemy import inspect, text


def upgrade(bound) -> list[str]:
    """Add preference columns. Safe to repeat. Does not create the user table."""
    from app.models.identity import User
    from app.models.workspace import WorkspaceSettings

    _add_missing_columns(bound, (User.__table__, WorkspaceSettings.__table__))
    return []


def _add_missing_columns(bound, tables) -> None:
    inspector = inspect(bound)
    dialect = bound.dialect
    for table in tables:
        if not inspector.has_table(table.name):
            continue
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing or column.primary_key:
                continue
            type_sql = column.type.compile(dialect=dialect)
            with bound.begin() as connection:
                connection.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {column.name} {type_sql}"))
            existing.add(column.name)
