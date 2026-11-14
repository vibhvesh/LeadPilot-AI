"""Idempotent schema step for Industry Pulse tables."""

from sqlalchemy import inspect, text


def upgrade(bound) -> list[str]:
    """Create pulse tables and add any columns that are missing. Safe to repeat."""
    from app.models.pulse import PulseComment, PulseItem

    tables = (PulseItem.__table__, PulseComment.__table__)
    inspector = inspect(bound)
    before = set(inspector.get_table_names())
    for table in tables:
        table.create(bind=bound, checkfirst=True)
    _add_missing_columns(bound, tables)
    after = set(inspect(bound).get_table_names())
    return sorted(after - before)


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
