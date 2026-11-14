"""Create story_messages and the overlay switch. Safe to repeat."""

from sqlalchemy import inspect, text


def upgrade(bound) -> list[str]:
    from app.models.story import StoryMessage
    from app.models.workspace import WorkspaceSettings

    created = []
    inspector = inspect(bound)
    if "story_messages" not in set(inspector.get_table_names()):
        StoryMessage.__table__.create(bind=bound)
        created.append("story_messages")
    _add_columns(bound, (WorkspaceSettings.__table__,))
    return created


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
