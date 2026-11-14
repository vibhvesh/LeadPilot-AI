"""Create outreach tables and the coverage columns. Safe to repeat."""

from sqlalchemy import inspect, text


def upgrade(bound) -> list[str]:
    from app.models.identity import User
    from app.models.outreach import LeadEvent, OutreachMessage, OutreachTemplate
    from app.models.workspace import WorkspaceSettings

    created = []
    inspector = inspect(bound)
    existing = set(inspector.get_table_names())
    for table in (OutreachTemplate.__table__, OutreachMessage.__table__, LeadEvent.__table__):
        if table.name not in existing:
            table.create(bind=bound)
            created.append(table.name)
    _add_columns(bound, (User.__table__, WorkspaceSettings.__table__))
    return sorted(created)


def _add_columns(bound, tables) -> None:
    inspector = inspect(bound)
    dialect = bound.dialect
    for table in tables:
        if not inspector.has_table(table.name):
            continue
        have = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in have or column.primary_key:
                continue
            type_sql = column.type.compile(dialect=dialect)
            with bound.begin() as connection:
                connection.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {column.name} {type_sql}"))
            have.add(column.name)
